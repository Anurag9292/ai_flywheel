"""``source-registry`` — derived in the public-data ingestion step.

> *The venture needs to: maintain (and let humans enrich) the list of public
> API sources to ingest from.*

An **event-driven node** (dumb) that owns the catalog of opaque data sources.
It does **not** know what any source *is* — it just persists a URL plus optional
human hints/enrichment, and announces the active set so the scraper can act.

- **Reacts to:** ``source.register.requested``, ``source.enrich.requested``.
- **Calls:** ``source-store``.
- **Emits:** ``sources.updated`` (carrying the enabled source ids).
- **Kind:** dumb.

Humans (or automated callers) enrich a source by sending ``source.enrich.requested``
with a ``source_id`` and any of: ``hints`` (override the scraper's inference),
``enrichment`` (free-form tags/notes), ``enabled``. Enrichment is merged onto the
stored source — the registry is the single place that knowledge accumulates.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.persistence.models import Source
from flywheel.persistence.source_store import InMemorySourceStore, SourceStore

# Machine enrichment: cheap, deterministic URL-pattern → (kind, tags) rules so a
# source registered with *just a URL* still gets classified without a human. The
# scraper stays schema-agnostic; this only annotates `enrichment.kind`, which the
# knowledge-builder uses to pick an extractor (jobs vs reviews) and the
# insight-inferrer uses for context. Extend this table as new domains arrive.
_ENRICHMENT_RULES: tuple[tuple[tuple[str, ...], str, tuple[str, ...]], ...] = (
    # (substrings to match in host+path, kind, tags)
    (("lever.co", "greenhouse.io", "ashbyhq.com", "/jobs", "/postings", "careers"),
     "ats-job-board", ("ats", "hiring-signal")),
    (("review", "ratings", "g2.com", "trustpilot", "capterra", "feedback"),
     "review-feed", ("reviews", "sentiment-signal")),
)


def infer_source_enrichment(url: str) -> dict[str, Any]:
    """Best-effort machine enrichment for a source URL.

    Returns a dict with an inferred ``kind`` and ``tags`` when a rule matches,
    else ``{}``. Deterministic and dependency-free — humans/explicit enrichment
    always override (we never clobber caller-supplied values; see ``_register``).
    """
    try:
        parsed = urlparse(url)
        haystack = f"{parsed.netloc}{parsed.path}".lower()
    except (ValueError, AttributeError):
        return {}
    for needles, kind, tags in _ENRICHMENT_RULES:
        if any(n in haystack for n in needles):
            return {"kind": kind, "tags": list(tags)}
    return {}


class SourceRegistry:
    name = "source-registry"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["source.register.requested", "source.enrich.requested"]
    emits = ["sources.updated"]
    calls = ["source-store"]

    def __init__(self, *, store: SourceStore | None = None) -> None:
        self._store = store or InMemorySourceStore()

    def handle(self, event: Event, ctx: NodeContext) -> None:
        if event.type == "source.register.requested":
            self._register(event)
        elif event.type == "source.enrich.requested":
            self._enrich(event)
        self._announce(event, ctx)

    # ── handlers ─────────────────────────────────────────────────────────────

    def _register(self, event: Event) -> None:
        """Register one source (or many via ``sources``)."""
        specs = event.payload.get("sources")
        if specs is None:
            specs = [event.payload]
        for spec in specs:
            url = spec.get("url", "")
            # Machine enrichment first, then layer caller-supplied values ON TOP
            # so explicit human/automated enrichment always wins (never clobbered).
            inferred = infer_source_enrichment(url)
            enrichment = dict(spec.get("enrichment", {}) or {})
            if "kind" in inferred and "kind" not in enrichment:
                enrichment["kind"] = inferred["kind"]
            tags = list(
                dict.fromkeys([*(inferred.get("tags", [])), *(spec.get("tags", []) or [])])
            )
            self._store.upsert(
                Source(
                    id=spec.get("id", ""),
                    venture_id=event.venture_id,
                    url=url,
                    auth_ref=spec.get("auth_ref", ""),
                    hints=spec.get("hints", {}) or {},
                    enrichment=enrichment,
                    tags=tags,
                    enabled=spec.get("enabled", True),
                )
            )

    def _enrich(self, event: Event) -> None:
        """Merge human-supplied hints / enrichment / enabled onto a source."""
        source_id = event.payload.get("source_id", "")
        existing = self._store.get(source_id)
        if existing is None:
            return
        updates: dict[str, Any] = {}
        if "hints" in event.payload:
            updates["hints"] = {**existing.hints, **(event.payload["hints"] or {})}
        if "enrichment" in event.payload:
            updates["enrichment"] = {
                **existing.enrichment,
                **(event.payload["enrichment"] or {}),
            }
        if "tags" in event.payload:
            merged = list(dict.fromkeys([*existing.tags, *(event.payload["tags"] or [])]))
            updates["tags"] = merged
        if "enabled" in event.payload:
            updates["enabled"] = bool(event.payload["enabled"])
        if updates:
            self._store.upsert(existing.model_copy(update=updates))

    def _announce(self, event: Event, ctx: NodeContext) -> None:
        enabled = self._store.list_enabled(event.venture_id)
        ctx.emit(
            type="sources.updated",
            payload={
                "source_ids": [s.id for s in enabled],
                "count": len(enabled),
            },
        )
