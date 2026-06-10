"""SQLAlchemy-backed stores (Neon Postgres) behind the store Protocols.

These satisfy the *same* contracts as the in-memory fakes — the conformance
suite (``test_persistence_stores`` assertions, reused by the gated Neon suite)
proves it. Nodes are constructed with these via ``reset_ingestion_stores(...)``
when ``DB_URL`` is set; nothing else changes.

Idempotency uses Postgres upserts (``ON CONFLICT``) so a re-scrape of a full
snapshot is a no-op and the knowledge-builder's re-runs are safe.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from flywheel.persistence.base import make_session_factory
from flywheel.persistence.models import (
    Edge,
    Entity,
    IngestPlan,
    MaterializedView,
    RawRecord,
    Source,
)
from flywheel.persistence.sql_models import (
    EdgeRow,
    EntityRow,
    MaterializedViewRow,
    RawRecordRow,
    SourceRow,
)


def _now() -> datetime:
    return datetime.now(UTC)


# ── SourceStore ────────────────────────────────────────────────────────────────


class SqlSourceStore:
    def __init__(self, db_url: str | None = None) -> None:
        self._session = make_session_factory(db_url)

    def upsert(self, source: Source) -> Source:
        sid = source.id or uuid.uuid4().hex
        with self._session() as s, s.begin():
            row = s.get(SourceRow, sid)
            now = _now()
            plan = source.ingest_plan.model_dump() if source.ingest_plan else None
            if row is None:
                row = SourceRow(id=sid, created_at=now)
                s.add(row)
            row.venture_id = source.venture_id
            row.url = source.url
            row.auth_ref = source.auth_ref
            row.hints = source.hints
            row.enrichment = source.enrichment
            row.tags = source.tags
            row.enabled = source.enabled
            if plan is not None:
                row.ingest_plan = plan
            row.schema_fingerprint = source.schema_fingerprint
            row.cursor = source.cursor
            row.updated_at = now
        return self.get(sid) or source

    def get(self, source_id: str) -> Source | None:
        with self._session() as s:
            row = s.get(SourceRow, source_id)
            return _source_from_row(row) if row else None

    def list_enabled(self, venture_id: str | None = None) -> list[Source]:
        with self._session() as s:
            stmt = select(SourceRow).where(SourceRow.enabled.is_(True))
            if venture_id is not None:
                stmt = stmt.where(SourceRow.venture_id == venture_id)
            stmt = stmt.order_by(SourceRow.created_at, SourceRow.id)
            return [_source_from_row(r) for r in s.scalars(stmt)]

    def save_state(
        self,
        source_id: str,
        *,
        ingest_plan: IngestPlan | None = None,
        schema_fingerprint: str | None = None,
        cursor: dict[str, Any] | None = None,
    ) -> None:
        with self._session() as s, s.begin():
            row = s.get(SourceRow, source_id)
            if row is None:
                return
            if ingest_plan is not None:
                row.ingest_plan = ingest_plan.model_dump()
            if schema_fingerprint is not None:
                row.schema_fingerprint = schema_fingerprint
            if cursor is not None:
                row.cursor = cursor
            row.updated_at = _now()


def _source_from_row(row: SourceRow) -> Source:
    return Source(
        id=row.id,
        venture_id=row.venture_id,
        url=row.url,
        auth_ref=row.auth_ref,
        hints=row.hints or {},
        enrichment=row.enrichment or {},
        tags=row.tags or [],
        enabled=row.enabled,
        ingest_plan=IngestPlan.model_validate(row.ingest_plan) if row.ingest_plan else None,
        schema_fingerprint=row.schema_fingerprint,
        cursor=row.cursor or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── RawRecordStore ─────────────────────────────────────────────────────────────


class SqlRawRecordStore:
    def __init__(self, db_url: str | None = None) -> None:
        self._session = make_session_factory(db_url)

    def upsert_many(self, records: list[RawRecord]) -> list[RawRecord]:
        if not records:
            return []
        new: list[RawRecord] = []
        with self._session() as s, s.begin():
            for rec in records:
                stmt = (
                    pg_insert(RawRecordRow)
                    .values(
                        source_id=rec.source_id,
                        venture_id=rec.venture_id,
                        external_id=rec.external_id,
                        raw=rec.raw,
                        source_timestamp=rec.source_timestamp,
                        ingested_at=_now(),
                    )
                    .on_conflict_do_nothing(constraint="uq_raw_source_external")
                    .returning(RawRecordRow.ingested_seq, RawRecordRow.ingested_at)
                )
                res = s.execute(stmt).first()
                if res is not None:
                    new.append(
                        rec.model_copy(
                            update={"ingested_seq": res[0], "ingested_at": res[1]}
                        )
                    )
        return new

    def read_since(self, seq: int, *, limit: int | None = None) -> list[RawRecord]:
        with self._session() as s:
            stmt = (
                select(RawRecordRow)
                .where(RawRecordRow.ingested_seq > seq)
                .order_by(RawRecordRow.ingested_seq)
            )
            if limit is not None:
                stmt = stmt.limit(limit)
            return [_raw_from_row(r) for r in s.scalars(stmt)]

    def max_seq(self, source_id: str | None = None) -> int:
        from sqlalchemy import func

        with self._session() as s:
            stmt = select(func.max(RawRecordRow.ingested_seq))
            if source_id is not None:
                stmt = stmt.where(RawRecordRow.source_id == source_id)
            return int(s.scalar(stmt) or 0)


def _raw_from_row(row: RawRecordRow) -> RawRecord:
    return RawRecord(
        source_id=row.source_id,
        venture_id=row.venture_id,
        external_id=row.external_id,
        raw=row.raw or {},
        source_timestamp=row.source_timestamp,
        ingested_seq=row.ingested_seq,
        ingested_at=row.ingested_at,
    )


# ── KnowledgeStore ─────────────────────────────────────────────────────────────


class SqlKnowledgeStore:
    def __init__(self, db_url: str | None = None) -> None:
        self._session = make_session_factory(db_url)

    def upsert_entities(self, entities: list[Entity]) -> None:
        with self._session() as s, s.begin():
            for ent in entities:
                row = s.scalar(
                    select(EntityRow).where(
                        EntityRow.venture_id == ent.venture_id,
                        EntityRow.type == ent.type,
                        EntityRow.key == ent.key,
                    )
                )
                if row is None:
                    s.add(
                        EntityRow(
                            type=ent.type,
                            key=ent.key,
                            venture_id=ent.venture_id,
                            props=ent.props,
                        )
                    )
                else:
                    row.props = {**(row.props or {}), **ent.props}

    def upsert_edges(self, edges: list[Edge]) -> None:
        with self._session() as s, s.begin():
            for e in edges:
                stmt = (
                    pg_insert(EdgeRow)
                    .values(
                        type=e.type,
                        src_type=e.src_type,
                        src_key=e.src_key,
                        dst_type=e.dst_type,
                        dst_key=e.dst_key,
                        venture_id=e.venture_id,
                        props=e.props,
                    )
                    .on_conflict_do_nothing(constraint="uq_edge_identity")
                )
                s.execute(stmt)

    def refresh_view(self, view: MaterializedView) -> None:
        with self._session() as s, s.begin():
            row = s.scalar(
                select(MaterializedViewRow).where(
                    MaterializedViewRow.venture_id == view.venture_id,
                    MaterializedViewRow.name == view.name,
                )
            )
            if row is None:
                s.add(
                    MaterializedViewRow(
                        name=view.name,
                        venture_id=view.venture_id,
                        rows=view.rows,
                        refreshed_at=_now(),
                    )
                )
            else:
                row.rows = view.rows
                row.refreshed_at = _now()

    def get_view(self, name: str, venture_id: str | None = None) -> MaterializedView | None:
        with self._session() as s:
            stmt = select(MaterializedViewRow).where(MaterializedViewRow.name == name)
            if venture_id is not None:
                stmt = stmt.where(MaterializedViewRow.venture_id == venture_id)
            row = s.scalars(stmt).first()
            if row is None:
                return None
            return MaterializedView(
                name=row.name,
                venture_id=row.venture_id,
                rows=row.rows or [],
                refreshed_at=row.refreshed_at,
            )

    def entities(self, type: str | None = None, venture_id: str | None = None) -> list[Entity]:
        with self._session() as s:
            stmt = select(EntityRow)
            if type is not None:
                stmt = stmt.where(EntityRow.type == type)
            if venture_id is not None:
                stmt = stmt.where(EntityRow.venture_id == venture_id)
            stmt = stmt.order_by(EntityRow.type, EntityRow.key)
            return [
                Entity(type=r.type, key=r.key, venture_id=r.venture_id, props=r.props or {})
                for r in s.scalars(stmt)
            ]

    def edges(self, type: str | None = None, venture_id: str | None = None) -> list[Edge]:
        with self._session() as s:
            stmt = select(EdgeRow)
            if type is not None:
                stmt = stmt.where(EdgeRow.type == type)
            if venture_id is not None:
                stmt = stmt.where(EdgeRow.venture_id == venture_id)
            stmt = stmt.order_by(EdgeRow.type, EdgeRow.src_key, EdgeRow.dst_key)
            return [
                Edge(
                    type=r.type,
                    src_type=r.src_type,
                    src_key=r.src_key,
                    dst_type=r.dst_type,
                    dst_key=r.dst_key,
                    venture_id=r.venture_id,
                    props=r.props or {},
                )
                for r in s.scalars(stmt)
            ]
