"""FastAPI dev introspection app.

Endpoints:

- ``GET  /api/health``   — liveness.
- ``GET  /api/topology`` — ``Runtime.describe()``: the code-derived node/event
  graph (visualization View 1).
- ``GET  /api/traces``   — captured ``trace.captured`` rows from the live
  in-memory runtime, grouped into ordered, causally-linked chains
  (visualization View 2).
- ``POST /api/publish``  — publish an event onto the live bus and run it through
  the real nodes; returns the resulting trace chain. **This is how the frontend
  triggers a real run** (no seeding).
- ``POST /api/reset``    — clear the in-memory traces (the durable
  ``traces.jsonl`` log is kept).

Run it:

    uv run uvicorn flywheel.devserver.app:app --reload --port 8000

This is a **dev-only, local, ephemeral** surface (state resets on restart), not
the venture runtime or a production API. It can now mutate state (publish), but
only onto its own in-process bus — durable, multi-process transport stays
deferred per ``new_docs/stack.md``. See ``new_docs/visualization.md``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from flywheel.env import load_dotenv_if_present

# Load a gitignored repo-root .env BEFORE the runtime is built, so FLYWHEEL_VENTURE
# / OPENAI_API_KEY / FIRECRAWL_API_KEY are in the environment when the registry
# reads them. Shell + debugger env still win (override=False). No-op without
# python-dotenv or a .env file.
load_dotenv_if_present()

from flywheel.core.events import Event  # noqa: E402  (after dotenv load)
from flywheel.core.timers import TimerSource  # noqa: E402
from flywheel.devserver.topology import (  # noqa: E402
    build_runtime,
    find_review_queue,
    load_default_venture,
    runtime_mode,
)
from flywheel.venture.registry import ingestion_stores  # noqa: E402
from flywheel.venture.view import function_view, lint_venture  # noqa: E402

app = FastAPI(
    title="AI Flywheel — Dev Introspection",
    description="Topology + trace introspection and event triggering. Dev only.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Where to persist run traces. Every node invocation appends one JSON line
# (node, latency, cost, correlation_id, emitted events, error) so runs survive a
# restart and are greppable. Repo-root traces.jsonl by default; override with
# FLYWHEEL_TRACE_LOG (e.g. in .env). Gitignored.
_TRACE_LOG = Path(os.environ.get("FLYWHEEL_TRACE_LOG", "traces.jsonl"))

# One long-lived runtime for the process. Its bus + nodes persist across
# requests; traces are held in memory (so /api/traces reads live state) *and*
# appended to _TRACE_LOG for a durable record.
_runtime, _bus, _recorder = build_runtime(trace_log=_TRACE_LOG, keep_in_memory=True)
# Capture the ingestion store bundle wired into *this* runtime's nodes at build
# time (the global can be reset by later build_runtime calls in the same
# process, e.g. tests — so bind it now to stay consistent with our nodes).
_ingestion = ingestion_stores()
# The venture definition that produced this runtime (Layer 2 composition).
_venture = load_default_venture()
# The human-review-queue holds parked items needing founder approval (Step 5).
_review_queue = find_review_queue(_runtime)
# Timer substrate: fires tick.* onto the live bus so timer-driven nodes
# (source-scraper, knowledge-builder, insight-inferrer) re-run on a cadence —
# this is what makes the ingestion flywheel keep turning "at a founder level".
_timer = TimerSource(_bus)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/topology")
def topology() -> dict[str, Any]:
    """The code-derived topology graph."""
    return _runtime.describe()


@app.get("/api/venture")
def venture() -> dict[str, Any]:
    """The Layer 2 venture composition: domain, functions, and venture lint.

    ``functions`` groups the live topology by function (each with the events it
    owns as inputs/outputs); ``lint`` cross-checks the venture's intended
    composition against the actual code-derived graph.
    """
    describe = _runtime.describe()
    return {
        "name": _venture.name,
        "description": _venture.description,
        "domain": _venture.domain,
        # "live" if lead-gen discovery hits real public ATS APIs, else "fake".
        # The /topology UI renders this as a LIVE/FAKE badge.
        "mode": runtime_mode(_venture),
        "functions": function_view(_venture, describe),
        "lint": lint_venture(_venture, describe),
    }


def _build_chain(correlation_id: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn a group of trace rows into an ordered, causally-linked chain.

    - sort chronologically by ``captured_at``
    - assign a ``seq`` index per step
    - link ``parent_step`` by matching this step's ``trigger_event_id`` against
      a prior step's ``emitted_event_ids`` (true parent->child causality)
    - flag ``is_start`` (no parent in this chain) and ``is_end`` (nothing
      downstream consumed what it emitted)
    """
    ordered = sorted(steps, key=lambda s: s.get("captured_at", ""))

    emitter_of: dict[str, int] = {}
    for i, step in enumerate(ordered):
        for eid in step.get("emitted_event_ids", []):
            emitter_of[eid] = i

    consumed_emitters: set[int] = set()
    for step in ordered:
        trig = step.get("trigger_event_id") or ""
        if trig in emitter_of:
            consumed_emitters.add(emitter_of[trig])

    enriched: list[dict[str, Any]] = []
    for i, step in enumerate(ordered):
        trig = step.get("trigger_event_id") or ""
        parent = emitter_of.get(trig)
        enriched.append(
            {
                **step,
                "seq": i,
                "parent_step": parent,
                "is_start": parent is None,
                "is_end": i not in consumed_emitters,
            }
        )

    return {"correlation_id": correlation_id, "steps": enriched}


def _chains_from(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("correlation_id", "unknown"), []).append(row)
    chains = [_build_chain(cid, steps) for cid, steps in grouped.items()]
    chains.sort(
        key=lambda c: c["steps"][0].get("captured_at", "") if c["steps"] else "",
        reverse=True,
    )
    return chains


@app.get("/api/traces")
def traces() -> dict[str, Any]:
    """Live captured trace rows + ordered, causally-linked chains."""
    rows = _recorder.traces
    return {"count": len(rows), "traces": rows, "chains": _chains_from(rows)}


class PublishRequest(BaseModel):
    type: str = Field(description="Event type, e.g. research.requested.")
    venture_id: str = "postlineai"
    payload: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/publish")
def publish(req: PublishRequest) -> dict[str, Any]:
    """Publish a real event onto the live bus and run it through the nodes.

    Returns the trace chain produced by *this* event's correlation id, so the
    frontend can immediately replay the run it just triggered.
    """
    event = Event(type=req.type, venture_id=req.venture_id, payload=req.payload)
    _bus.publish(event)

    # Collect just the rows for this run (its correlation id).
    rows = [r for r in _recorder.traces if r.get("correlation_id") == event.correlation_id]
    chains = _chains_from(rows)
    return {
        "correlation_id": event.correlation_id,
        "published": {"type": event.type, "venture_id": event.venture_id},
        "chain": chains[0] if chains else {"correlation_id": event.correlation_id, "steps": []},
    }


class TickRequest(BaseModel):
    period: str = "daily"
    venture_id: str = "postlineai"


@app.post("/api/tick")
def tick(req: TickRequest) -> dict[str, Any]:
    """Fire a ``tick.<period>`` onto the live bus (manual scheduler pulse).

    Timer-driven ingestion nodes re-run: the scraper re-fetches sources
    (resumable + idempotent), the builder folds in any new records, and the
    insight-inferrer re-reasons. Returns this pulse's trace chain.
    """
    event = _timer.tick(req.period, venture_id=req.venture_id)
    rows = [r for r in _recorder.traces if r.get("correlation_id") == event.correlation_id]
    chains = _chains_from(rows)
    return {
        "correlation_id": event.correlation_id,
        "published": {"type": event.type, "venture_id": event.venture_id},
        "chain": chains[0] if chains else {"correlation_id": event.correlation_id, "steps": []},
    }


@app.post("/api/reset")
def reset() -> dict[str, Any]:
    """Clear the in-memory traces so the UI can start clean.

    This only clears the live in-memory view; the durable ``traces.jsonl`` log
    is intentionally left intact (it's the run record, not a UI buffer).
    """
    _recorder.clear()
    return {"status": "cleared", "count": 0}


@app.get("/api/review")
def review_pending() -> dict[str, Any]:
    """List items parked in the human-review-queue awaiting founder approval.

    This is the visible side of the Wizard-of-Oz human-in-the-loop: drafts that
    arrived tagged ``requires_human`` and are waiting for the founder to write /
    approve the real post (Step 5).
    """
    pending = _review_queue.pending() if _review_queue is not None else []
    return {"count": len(pending), "pending": pending}


class ApproveRequest(BaseModel):
    event_id: str = Field(description="The parked event_id to approve.")
    venture_id: str = "postlineai"
    draft: str | None = Field(
        default=None, description="Optional final text the founder ghostwrote."
    )


@app.get("/api/ingestion/sources")
def ingestion_sources() -> dict[str, Any]:
    """The registered data sources with their inferred plan + resume cursor.

    The read side of the public-data ingestion cluster: shows each source the
    ``source-registry`` knows about, whether its schema has been inferred yet,
    and where its scrape cursor is — i.e. "till what point we have gotten the
    info".
    """
    sources = _ingestion.source.list_enabled("postlineai")
    return {
        "count": len(sources),
        "sources": [
            {
                "id": s.id,
                "url": s.url,
                "enabled": s.enabled,
                "tags": s.tags,
                "enrichment": s.enrichment,
                "schema_fingerprint": s.schema_fingerprint,
                "ingest_plan": s.ingest_plan.model_dump() if s.ingest_plan else None,
                "cursor": s.cursor,
            }
            for s in sources
        ],
    }


@app.get("/api/ingestion/knowledge")
def ingestion_knowledge(view: str = "open_roles_by_company") -> dict[str, Any]:
    """The knowledge-builder output: a materialized view + graph counts.

    ``view`` selects which materialized view to return (default:
    ``open_roles_by_company``; also ``job_catalog``, ``recent_sentiment_by_company``).
    Entity/edge counts give a quick sense of the graph size built from records.
    """
    store = _ingestion.knowledge
    mv = store.get_view(view, "postlineai")
    return {
        "view": view,
        "rows": mv.rows if mv else [],
        "refreshed_at": mv.refreshed_at.isoformat() if mv else None,
        "entity_counts": {
            t: len(store.entities(type=t, venture_id="postlineai"))
            for t in ("Company", "Job", "Department", "Location", "Review", "Product")
        },
        "edge_count": len(store.edges(venture_id="postlineai")),
    }


@app.post("/api/review/approve")
def review_approve(req: ApproveRequest) -> dict[str, Any]:
    """Approve a parked item: publishes ``review.approved`` to resume the chain.

    This is the *second* run of the park-and-resume flow — it re-enters the bus
    and the human-review-queue re-emits the expected result type (e.g.
    ``post.approved``), which the post-scheduler then publishes. Returns the
    resulting trace chain for the resumed run.

    The approval event reuses the *parked item's* ``correlation_id`` so the
    resume threads onto the original draft run — the two runs (park, then
    resume) appear as one continuous draft→approve→publish chain in the
    timeline, rather than a disconnected fragment.
    """
    payload: dict[str, Any] = {"event_id": req.event_id}
    if req.draft is not None:
        payload["draft"] = req.draft

    # Reuse the parked item's correlation id so the resumed run threads onto the
    # original draft run. Falls back to a fresh id if the item isn't found.
    pending = _review_queue.pending() if _review_queue is not None else []
    parked_correlation = next(
        (p["correlation_id"] for p in pending if p["event_id"] == req.event_id),
        None,
    )
    event = (
        Event(
            type="review.approved",
            venture_id=req.venture_id,
            correlation_id=parked_correlation,
            payload=payload,
        )
        if parked_correlation is not None
        else Event(type="review.approved", venture_id=req.venture_id, payload=payload)
    )
    _bus.publish(event)

    rows = [r for r in _recorder.traces if r.get("correlation_id") == event.correlation_id]
    chains = _chains_from(rows)
    return {
        "correlation_id": event.correlation_id,
        "approved": req.event_id,
        "chain": chains[0] if chains else {"correlation_id": event.correlation_id, "steps": []},
    }


# ── Optional autonomous scheduler ──────────────────────────────────────────────
#
# Set FLYWHEEL_TICK_SECONDS=<n> to have the server fire tick.daily every n
# seconds in a background thread, so the ingestion flywheel self-runs without a
# manual /api/tick call. Off by default (deterministic dev/tests). In production
# a real cron / Temporal cron workflow drives /api/tick behind the same surface.
def _start_auto_ticker() -> None:
    raw = os.environ.get("FLYWHEEL_TICK_SECONDS", "").strip()
    if not raw:
        return
    try:
        interval = float(raw)
    except ValueError:
        return
    if interval <= 0:
        return

    import threading

    venture = os.environ.get("FLYWHEEL_VENTURE", "postlineai") or "postlineai"

    def _loop() -> None:
        import time

        while True:
            time.sleep(interval)
            try:
                _timer.tick_daily(venture_id=venture)
            except Exception:  # noqa: BLE001 - a scheduler must never crash the server
                continue

    threading.Thread(target=_loop, name="flywheel-auto-ticker", daemon=True).start()


_start_auto_ticker()
