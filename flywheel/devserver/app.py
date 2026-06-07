"""FastAPI dev introspection app.

Endpoints (read-only):

- ``GET /api/health``   — liveness.
- ``GET /api/topology`` — ``Runtime.describe()``: the code-derived node/event
  graph (visualization View 1).
- ``GET /api/traces``   — parsed ``trace.captured`` rows from ``traces.jsonl``,
  grouped into causal chains by ``correlation_id`` (visualization View 2).

Run it:

    uv run uvicorn flywheel.devserver.app:app --reload --port 8000

CORS is open to localhost dev origins only; this server must never be exposed
publicly (see the caveat in ``new_docs/visualization.md``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flywheel.devserver.topology import DEFAULT_TRACE_LOG, build_runtime

app = FastAPI(
    title="AI Flywheel — Dev Introspection",
    description="Read-only topology + trace introspection for visualization. Dev only.",
    version="0.1.0",
)

# Next dev server origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# A single runtime describes the current topology. Rebuilt cheaply per process.
_runtime = build_runtime()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/topology")
def topology() -> dict[str, Any]:
    """The code-derived topology graph."""
    return _runtime.describe()


def _load_traces(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _build_chain(correlation_id: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn a group of trace rows into an ordered, causally-linked chain.

    - sort chronologically by ``captured_at``
    - assign a ``seq`` index per step
    - link ``parent_step`` by matching this step's ``trigger_event_id`` against
      a prior step's ``emitted_event_ids`` (true parent->child causality)
    - flag ``is_start`` (no parent in this chain) and ``is_end`` (emitted
      nothing, or nothing downstream consumed what it emitted)
    """
    ordered = sorted(steps, key=lambda s: s.get("captured_at", ""))

    # event_id -> seq index of the step that emitted it.
    emitter_of: dict[str, int] = {}
    for i, step in enumerate(ordered):
        for eid in step.get("emitted_event_ids", []):
            emitter_of[eid] = i

    # Which steps were consumed downstream (their emitted ids became a trigger).
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


@app.get("/api/traces")
def traces() -> dict[str, Any]:
    """Parsed trace.captured rows, plus chains grouped by correlation_id.

    Each chain is one causal run (a published event + every node reaction it
    triggered), ordered chronologically and linked parent->child — exactly what
    the chronological timeline / replay view animates.
    """
    rows = _load_traces(DEFAULT_TRACE_LOG)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("correlation_id", "unknown"), []).append(row)

    chains = [_build_chain(cid, steps) for cid, steps in grouped.items()]
    # Most-recent run first (by the start step's timestamp).
    chains.sort(
        key=lambda c: c["steps"][0].get("captured_at", "") if c["steps"] else "",
        reverse=True,
    )

    return {"count": len(rows), "traces": rows, "chains": chains}
