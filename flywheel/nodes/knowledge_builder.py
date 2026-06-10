"""``knowledge-builder`` — derived in the public-data ingestion step.

> *The venture needs to: run through the stored records (only the newly-added
> ones) and turn them into something easy to consume — a knowledge graph and
> materialized views.*

An **event-driven node** (dumb, with an ``Extractor`` seam so an LLM-based
extractor can swap in later) that reads **only new** raw records since its own
watermark and builds:

  - **Knowledge graph:** ``Entity`` nodes + typed ``Edge`` relationships.
  - **Materialized views:** denormalized rollups consumers read directly.

- **Reacts to:** ``source.records.ingested``, ``tick.daily``.
- **Calls:** ``raw-record-store`` (read new), ``knowledge-store`` (write).
- **Emits:** ``knowledge.updated``.
- **Kind:** dumb (the default ``StructuralExtractor`` is deterministic; an
  ``LLMExtractor`` can replace it behind the same seam — see Step-7-style swap).

The default extractor is **generic**: it does not assume any provider's field
names. It uses the source's inferred ``IngestPlan`` field map (carried on the
raw record) plus a small set of conventional aliases to pull out a title, a
company, and grouping dimensions. Anything it can't map is preserved in the
entity ``props`` so no information is lost.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.persistence.knowledge_store import (
    InMemoryKnowledgeStore,
    KnowledgeStore,
)
from flywheel.persistence.models import Edge, Entity, MaterializedView, RawRecord
from flywheel.persistence.raw_record_store import (
    InMemoryRawRecordStore,
    RawRecordStore,
)


@runtime_checkable
class Extractor(Protocol):
    """Turn one raw record into graph entities + edges. Swappable (dumb→LLM)."""

    version: str

    def extract(self, record: RawRecord) -> tuple[list[Entity], list[Edge]]: ...


# Conventional field aliases, tried in order. Generic — not provider-specific.
_TITLE_KEYS = ("title", "text", "name", "headline")
_COMPANY_KEYS = ("company", "company_name", "organization", "org")
_DEPT_KEYS = ("department", "dept", "team")
_LOCATION_KEYS = ("location", "city", "office")


def _first(raw: dict[str, Any], keys: tuple[str, ...]) -> str:
    for k in keys:
        v = raw.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            # e.g. {"name": "..."} (Greenhouse location) or nested category.
            inner = v.get("name") or v.get("location")
            if isinstance(inner, str) and inner.strip():
                return inner.strip()
    return ""


class StructuralExtractor:
    """Deterministic, generic extractor. The dumb default.

    Builds a ``Job`` entity per record and links it to ``Company`` /
    ``Department`` / ``Location`` entities when those dimensions are present.
    Company falls back to the source-derived enrichment (the venture seeds it).
    """

    version = "structural-1"

    def extract(self, record: RawRecord) -> tuple[list[Entity], list[Edge]]:
        raw = record.raw or {}
        vid = record.venture_id
        title = _first(raw, _TITLE_KEYS) or record.external_id
        # Company: explicit field, else the nested categories, else "" (the
        # scraper/venture may stamp it into raw under "_company").
        company = _first(raw, _COMPANY_KEYS) or str(raw.get("_company", ""))
        dept = _first(raw, _DEPT_KEYS) or _first(raw.get("categories", {}) or {}, _DEPT_KEYS)
        location = _first(raw, _LOCATION_KEYS) or _first(
            raw.get("categories", {}) or {}, _LOCATION_KEYS
        )

        job_key = f"{record.source_id}:{record.external_id}"
        entities: list[Entity] = [
            Entity(
                type="Job",
                key=job_key,
                venture_id=vid,
                props={
                    "title": title,
                    "company": company,
                    "department": dept,
                    "location": location,
                    "source_id": record.source_id,
                    "external_id": record.external_id,
                },
            )
        ]
        edges: list[Edge] = []
        if company:
            entities.append(Entity(type="Company", key=company, venture_id=vid, props={}))
            edges.append(
                Edge(
                    type="posts",
                    src_type="Company",
                    src_key=company,
                    dst_type="Job",
                    dst_key=job_key,
                    venture_id=vid,
                )
            )
        if dept:
            entities.append(Entity(type="Department", key=dept, venture_id=vid, props={}))
            edges.append(
                Edge(
                    type="in_department",
                    src_type="Job",
                    src_key=job_key,
                    dst_type="Department",
                    dst_key=dept,
                    venture_id=vid,
                )
            )
        if location:
            entities.append(Entity(type="Location", key=location, venture_id=vid, props={}))
            edges.append(
                Edge(
                    type="in_location",
                    src_type="Job",
                    src_key=job_key,
                    dst_type="Location",
                    dst_key=location,
                    venture_id=vid,
                )
            )
        return entities, edges


class KnowledgeBuilder:
    name = "knowledge-builder"
    reacts_to = ["source.records.ingested", "tick.daily"]
    emits = ["knowledge.updated"]
    calls = ["raw-record-store", "knowledge-store"]

    def __init__(
        self,
        *,
        raw_store: RawRecordStore | None = None,
        knowledge_store: KnowledgeStore | None = None,
        extractor: Extractor | None = None,
    ) -> None:
        self._raw = raw_store or InMemoryRawRecordStore()
        self._knowledge = knowledge_store or InMemoryKnowledgeStore()
        self._extractor = extractor or StructuralExtractor()
        # Binding reflected in version/kind for the trace (mirrors post-drafter).
        self.version = f"0.1.0-{self._extractor.version}"
        self.kind = "agentic" if "llm" in self._extractor.version else "dumb"
        # The builder's own incremental watermark over the raw store.
        self._watermark = 0

    def handle(self, event: Event, ctx: NodeContext) -> None:
        new_records = self._raw.read_since(self._watermark)
        if not new_records:
            return

        all_entities: list[Entity] = []
        all_edges: list[Edge] = []
        for rec in new_records:
            ents, edges = self._extractor.extract(rec)
            all_entities.extend(ents)
            all_edges.extend(edges)
            self._watermark = max(self._watermark, rec.ingested_seq)

        self._knowledge.upsert_entities(all_entities)
        self._knowledge.upsert_edges(all_edges)
        self._refresh_views(event.venture_id)

        ctx.emit(
            type="knowledge.updated",
            payload={
                "new_records": len(new_records),
                "entities_upserted": len(all_entities),
                "edges_upserted": len(all_edges),
                "watermark": self._watermark,
            },
        )

    def _refresh_views(self, venture_id: str) -> None:
        """Rebuild denormalized rollups from the current graph (idempotent)."""
        jobs = self._knowledge.entities(type="Job", venture_id=venture_id)
        # View 1: open roles by company (the consumable lead signal).
        by_company: dict[str, list[str]] = {}
        for j in jobs:
            company = j.props.get("company") or "(unknown)"
            by_company.setdefault(company, []).append(j.props.get("title", ""))
        roles_rows = [
            {"company": c, "open_roles": len(titles), "titles": sorted(t for t in titles if t)}
            for c, titles in sorted(by_company.items())
        ]
        self._knowledge.refresh_view(
            MaterializedView(name="open_roles_by_company", venture_id=venture_id, rows=roles_rows)
        )
        # View 2: a flat catalog of all jobs (easy to query/scan).
        catalog_rows = [
            {
                "company": j.props.get("company", ""),
                "title": j.props.get("title", ""),
                "department": j.props.get("department", ""),
                "location": j.props.get("location", ""),
            }
            for j in jobs
        ]
        self._knowledge.refresh_view(
            MaterializedView(name="job_catalog", venture_id=venture_id, rows=catalog_rows)
        )
