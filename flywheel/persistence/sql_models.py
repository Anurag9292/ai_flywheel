"""SQLAlchemy ORM tables for the ingestion stores (Neon Postgres).

These map to/from the Pydantic interface models in ``models.py`` — nodes never
see these rows. JSON columns hold the flexible/opaque parts (raw records, props,
hints, cursor) so the schema does not have to know any source's shape, matching
the "infer schema at runtime" design.

The ``raw_records`` monotonic watermark uses an autoincrement primary key
(``ingested_seq``) so ``read_since(seq)`` is a simple ``WHERE ingested_seq > :seq``.

Materialized views: the ``knowledge-builder`` writes denormalized rollups; on
Postgres these are stored as refreshable rows in ``materialized_views`` (a real
``MATERIALIZED VIEW`` is an optional optimization — the table form keeps the
fake and SQL impls identical in behavior, which the conformance suite requires).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    venture_id: Mapped[str] = mapped_column(String, index=True, default="")
    url: Mapped[str] = mapped_column(String, default="")
    auth_ref: Mapped[str] = mapped_column(String, default="")
    hints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    enrichment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tags: Mapped[list[Any]] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ingest_plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    schema_fingerprint: Mapped[str] = mapped_column(String, default="")
    cursor: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RawRecordRow(Base):
    __tablename__ = "raw_records"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_raw_source_external"),
    )

    ingested_seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String, index=True, default="")
    venture_id: Mapped[str] = mapped_column(String, index=True, default="")
    external_id: Mapped[str] = mapped_column(String, default="")
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EntityRow(Base):
    __tablename__ = "kg_entities"
    __table_args__ = (
        UniqueConstraint("venture_id", "type", "key", name="uq_entity_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, index=True, default="")
    key: Mapped[str] = mapped_column(String, default="")
    venture_id: Mapped[str] = mapped_column(String, index=True, default="")
    props: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class EdgeRow(Base):
    __tablename__ = "kg_edges"
    __table_args__ = (
        UniqueConstraint(
            "venture_id",
            "type",
            "src_type",
            "src_key",
            "dst_type",
            "dst_key",
            name="uq_edge_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, index=True, default="")
    src_type: Mapped[str] = mapped_column(String, default="")
    src_key: Mapped[str] = mapped_column(String, default="")
    dst_type: Mapped[str] = mapped_column(String, default="")
    dst_key: Mapped[str] = mapped_column(String, default="")
    venture_id: Mapped[str] = mapped_column(String, index=True, default="")
    props: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class MaterializedViewRow(Base):
    __tablename__ = "materialized_views"
    __table_args__ = (
        UniqueConstraint("venture_id", "name", name="uq_view_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, index=True, default="")
    venture_id: Mapped[str] = mapped_column(String, index=True, default="")
    rows: Mapped[list[Any]] = mapped_column(JSON, default=list)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
