"""Gated Neon integration tests for the real SQLAlchemy stores.

These run **only** when ``RUN_DB_TESTS=1`` and ``DB_URL`` point at a reachable
Postgres (a Neon branch in CI/dev). They prove the ``Sql*`` impls satisfy the
same contract the in-memory fakes do, and that the full ingestion flow works
end-to-end against a real database.

By default they are skipped, so the normal suite stays zero-infra.

Each test uses a unique ``venture_id`` so concurrent runs / shared test DBs do
not collide (true isolation comes from a Neon branch per run).
"""

from __future__ import annotations

import os
import uuid

import pytest

RUN = os.environ.get("RUN_DB_TESTS") == "1" and bool(os.environ.get("DB_URL"))

pytestmark = pytest.mark.skipif(
    not RUN, reason="set RUN_DB_TESTS=1 and DB_URL to run Neon integration tests"
)


@pytest.fixture(scope="module", autouse=True)
def _schema():
    from flywheel.persistence.base import create_all

    create_all()
    yield


def _vid() -> str:
    return f"itest-{uuid.uuid4().hex[:8]}"


def test_sql_source_store_roundtrip_and_state() -> None:
    from flywheel.persistence.models import IngestPlan, Source
    from flywheel.persistence.sql_stores import SqlSourceStore

    store = SqlSourceStore()
    vid = _vid()
    saved = store.upsert(Source(venture_id=vid, url="https://x/y"))
    assert saved.id
    store.save_state(
        saved.id,
        ingest_plan=IngestPlan(id_field="uuid"),
        schema_fingerprint="fp",
        cursor={"value": 5},
    )
    got = store.get(saved.id)
    assert got is not None
    assert got.ingest_plan is not None and got.ingest_plan.id_field == "uuid"
    assert got.cursor == {"value": 5}
    assert [s.id for s in store.list_enabled(vid)] == [saved.id]


def test_sql_raw_store_idempotent_and_incremental() -> None:
    from flywheel.persistence.models import RawRecord
    from flywheel.persistence.sql_stores import SqlRawRecordStore

    store = SqlRawRecordStore()
    sid = f"src-{uuid.uuid4().hex[:8]}"
    vid = _vid()

    def rec(ext: str) -> RawRecord:
        return RawRecord(source_id=sid, venture_id=vid, external_id=ext, raw={"k": ext})

    new1 = store.upsert_many([rec("1"), rec("2")])
    assert len(new1) == 2
    watermark = max(r.ingested_seq for r in new1)
    # Idempotent: same keys add nothing.
    new2 = store.upsert_many([rec("1"), rec("2"), rec("3")])
    assert [r.external_id for r in new2] == ["3"]
    fresh = store.read_since(watermark)
    assert any(r.external_id == "3" for r in fresh)
    assert store.max_seq(sid) >= 3


def test_sql_knowledge_store_graph_and_view() -> None:
    from flywheel.persistence.models import Edge, Entity, MaterializedView
    from flywheel.persistence.sql_stores import SqlKnowledgeStore

    store = SqlKnowledgeStore()
    vid = _vid()
    store.upsert_entities([Entity(type="Company", key="Acme", venture_id=vid, props={"a": 1})])
    store.upsert_entities([Entity(type="Company", key="Acme", venture_id=vid, props={"b": 2})])
    ents = store.entities(type="Company", venture_id=vid)
    assert len(ents) == 1 and ents[0].props == {"a": 1, "b": 2}

    e = Edge(
        type="posts",
        src_type="Company",
        src_key="Acme",
        dst_type="Job",
        dst_key="j1",
        venture_id=vid,
    )
    store.upsert_edges([e, e])
    assert len(store.edges(venture_id=vid)) == 1

    store.refresh_view(MaterializedView(name="roles", venture_id=vid, rows=[{"n": 1}]))
    store.refresh_view(MaterializedView(name="roles", venture_id=vid, rows=[{"n": 2}]))
    view = store.get_view("roles", vid)
    assert view is not None and view.rows == [{"n": 2}]


def test_sql_full_ingestion_flow() -> None:
    from flywheel.core.events import Event
    from flywheel.devserver.topology import build_runtime
    from flywheel.nodes._ingestion_seed import seed_register_payload
    from flywheel.persistence.sql_stores import (
        SqlKnowledgeStore,
        SqlRawRecordStore,
        SqlSourceStore,
    )
    from flywheel.venture.registry import reset_ingestion_stores

    # Back the cluster with real Neon stores for this build.
    reset_ingestion_stores(
        source=SqlSourceStore(),
        raw=SqlRawRecordStore(),
        knowledge=SqlKnowledgeStore(),
    )
    _, bus, _ = build_runtime(keep_in_memory=True)
    ingested: list[Event] = []
    insights: list[Event] = []
    bus.subscribe("source.records.ingested", ingested.append)
    bus.subscribe("market.insight", insights.append)

    bus.publish(
        Event(
            type="source.register.requested",
            venture_id="postlineai",
            payload=seed_register_payload(),
        )
    )
    assert sum(e.payload["new_count"] for e in ingested) >= 1
    # The insight-inferrer reasoned over the Neon-backed graph and surfaced at
    # least one founder-facing market insight.
    assert any(i.payload.get("kind") == "lead_opportunity" for i in insights)
