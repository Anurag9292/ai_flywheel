"""Domain models for the ingestion stores (Pydantic — transport/value types).

These are the **interface types** every store Protocol speaks, independent of
whether the backing store is the in-memory fake or SQLAlchemy/Neon. The SQL
ORM tables (``flywheel/persistence/sql_models.py``) map *to and from* these, so
nodes only ever touch these Pydantic models — never ORM rows.

Naming mirrors the rest of Layer 1: plain Pydantic ``BaseModel`` with defaults
so a partially-known record still validates.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ── Sources ───────────────────────────────────────────────────────────────────


class Pagination(BaseModel):
    """The paging mechanism the scraper should drive.

    ``kind``:
      - ``"none"``        — single full snapshot (fetch once).
      - ``"cursor"``      — response carries a next-page token at ``token_path``;
                            sent back via the ``param`` query parameter.
      - ``"offset"``      — increment ``param`` by ``page_size`` until empty.
      - ``"link_header"`` — follow RFC 5988 ``Link: rel="next"`` headers.
    """

    kind: str = "none"
    token_path: str = ""
    param: str = ""
    page_size: int = 0


class IngestPlan(BaseModel):
    """How to *read* a source — inferred by the agentic scraper (or human hints).

    Deliberately source-agnostic: the scraper infers these at runtime from a
    fetched sample (see ``flywheel/core/inferencer.py``); it does **not** know
    Lever/Greenhouse/Ashby. Human-supplied hints override inferred values.

    - ``record_path``     — dotted path to the list of records in the response
                            (``""`` / ``"$root"`` means the body itself is the list).
    - ``id_field``        — field within a record that uniquely identifies it.
    - ``timestamp_field`` — field used as the incremental cursor (may be ``""``).
    - ``timestamp_format``— ``"epoch_ms" | "epoch_s" | "iso8601" | ""``.
    - ``pagination``      — how to page (see :class:`Pagination`).
    - ``content_type``    — ``"json" | "rss" | "html"`` (negotiated at fetch).
    - ``confidence``      — inferencer's self-rated confidence in [0, 1].
    """

    record_path: str = ""
    id_field: str = "id"
    timestamp_field: str = ""
    timestamp_format: str = ""
    pagination: Pagination = Field(default_factory=Pagination)
    content_type: str = "json"
    confidence: float = 1.0


class Source(BaseModel):
    """An opaque, human-registerable data source.

    The registry stores these; the scraper reads them. Everything the scraper
    needs to *resume* lives here (``ingest_plan``, ``schema_fingerprint``,
    ``cursor``), so a scheduled re-run picks up exactly where it left off.
    """

    id: str = ""
    venture_id: str = ""
    url: str = ""
    # Opaque reference to credentials resolved at fetch time (never the secret).
    auth_ref: str = ""
    # Optional human hints that OVERRIDE inference (any subset of IngestPlan).
    hints: dict[str, Any] = Field(default_factory=dict)
    # Free-form human/automated enrichment (tags, notes, classifications).
    enrichment: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True

    # Inferred-once-and-cached ingestion state.
    ingest_plan: IngestPlan | None = None
    schema_fingerprint: str = ""
    # Opaque resume cursor: ``{"strategy": ..., "value": ...}`` (scraper-defined).
    cursor: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# ── Raw records ─────────────────────────────────────────────────────────────--


class RawRecord(BaseModel):
    """One ingested record, stored verbatim plus the fields we extracted.

    ``ingested_seq`` is a per-store monotonic watermark: the knowledge-builder
    reads ``read_since(seq)`` to process only *newly added* rows incrementally.
    Idempotency key is ``(source_id, external_id)``.
    """

    source_id: str = ""
    venture_id: str = ""
    external_id: str = ""
    # The verbatim record as returned by the source (post-parse, pre-normalize).
    raw: dict[str, Any] = Field(default_factory=dict)
    # Normalized cursor timestamp (UTC) when the source exposed one.
    source_timestamp: datetime | None = None
    ingested_seq: int = 0
    ingested_at: datetime = Field(default_factory=_utcnow)


# ── Knowledge graph + materialized views ──────────────────────────────────────


class Entity(BaseModel):
    """A node in the knowledge graph (Company, Job, Department, Team, Location…).

    ``key`` is the natural identity within ``type`` (e.g. company name, job id)
    used for idempotent upserts; ``props`` holds the denormalized attributes.
    """

    type: str = ""
    key: str = ""
    venture_id: str = ""
    props: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    """A typed relationship between two entities (e.g. company -posts-> job)."""

    type: str = ""
    src_type: str = ""
    src_key: str = ""
    dst_type: str = ""
    dst_key: str = ""
    venture_id: str = ""
    props: dict[str, Any] = Field(default_factory=dict)


class MaterializedView(BaseModel):
    """A denormalized, ready-to-consume rollup the knowledge-builder refreshes.

    On Postgres these become real ``MATERIALIZED VIEW``s (or refreshable
    tables); the fake just stores the rows. Consumers read ``rows`` directly.
    """

    name: str = ""
    venture_id: str = ""
    rows: list[dict[str, Any]] = Field(default_factory=list)
    refreshed_at: datetime = Field(default_factory=_utcnow)
