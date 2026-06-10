"""Store conformance tests.

These run against the in-memory fakes (zero infra). The same assertions are
reused by the gated Neon integration suite (``test_persistence_neon.py``) so the
``Sql*`` impls must satisfy the identical contract.
"""

from __future__ import annotations

from datetime import UTC, datetime

from flywheel.persistence.knowledge_store import InMemoryKnowledgeStore
from flywheel.persistence.models import (
    Edge,
    Entity,
    IngestPlan,
    MaterializedView,
    RawRecord,
    Source,
)
from flywheel.persistence.raw_record_store import InMemoryRawRecordStore
from flywheel.persistence.source_store import InMemorySourceStore

# ── SourceStore ────────────────────────────────────────────────────────────────


def test_source_store_upsert_assigns_id_and_roundtrips() -> None:
    store = InMemorySourceStore()
    saved = store.upsert(Source(venture_id="v", url="https://x/y"))
    assert saved.id
    got = store.get(saved.id)
    assert got is not None and got.url == "https://x/y"


def test_source_store_list_enabled_scopes_by_venture() -> None:
    store = InMemorySourceStore()
    store.upsert(Source(venture_id="v1", url="a", enabled=True))
    store.upsert(Source(venture_id="v2", url="b", enabled=True))
    store.upsert(Source(venture_id="v1", url="c", enabled=False))
    assert [s.url for s in store.list_enabled("v1")] == ["a"]
    assert {s.url for s in store.list_enabled()} == {"a", "b"}


def test_source_store_save_state_persists_resume_fields() -> None:
    store = InMemorySourceStore()
    s = store.upsert(Source(venture_id="v", url="u"))
    plan = IngestPlan(id_field="uuid", timestamp_field="createdAt")
    store.save_state(
        s.id, ingest_plan=plan, schema_fingerprint="fp1", cursor={"value": 42}
    )
    got = store.get(s.id)
    assert got is not None
    assert got.ingest_plan is not None and got.ingest_plan.id_field == "uuid"
    assert got.schema_fingerprint == "fp1"
    assert got.cursor == {"value": 42}


# ── RawRecordStore ─────────────────────────────────────────────────────────────


def _rec(sid: str, ext: str) -> RawRecord:
    return RawRecord(source_id=sid, venture_id="v", external_id=ext, raw={"k": ext})


def test_raw_store_idempotent_on_source_and_external_id() -> None:
    store = InMemoryRawRecordStore()
    new1 = store.upsert_many([_rec("s", "1"), _rec("s", "2")])
    assert len(new1) == 2
    # Re-ingesting the same keys adds nothing (the resume guarantee).
    new2 = store.upsert_many([_rec("s", "1"), _rec("s", "2"), _rec("s", "3")])
    assert [r.external_id for r in new2] == ["3"]
    assert store.max_seq("s") == 3


def test_raw_store_read_since_is_incremental_and_ordered() -> None:
    store = InMemoryRawRecordStore()
    store.upsert_many([_rec("s", "1"), _rec("s", "2")])
    watermark = store.max_seq()
    store.upsert_many([_rec("s", "3")])
    fresh = store.read_since(watermark)
    assert [r.external_id for r in fresh] == ["3"]
    assert all(r.ingested_seq > watermark for r in fresh)


def test_raw_store_max_seq_scopes_by_source() -> None:
    store = InMemoryRawRecordStore()
    store.upsert_many([_rec("a", "1"), _rec("b", "1"), _rec("a", "2")])
    assert store.max_seq("a") == 3  # 'a' got seq 1 and 3
    assert store.max_seq("b") == 2
    assert store.max_seq() == 3


# ── KnowledgeStore ─────────────────────────────────────────────────────────────


def test_knowledge_store_entity_upsert_merges_props() -> None:
    store = InMemoryKnowledgeStore()
    store.upsert_entities([Entity(type="Company", key="Acme", venture_id="v", props={"a": 1})])
    store.upsert_entities([Entity(type="Company", key="Acme", venture_id="v", props={"b": 2})])
    ents = store.entities(type="Company", venture_id="v")
    assert len(ents) == 1 and ents[0].props == {"a": 1, "b": 2}


def test_knowledge_store_edges_idempotent() -> None:
    store = InMemoryKnowledgeStore()
    e = Edge(
        type="posts",
        src_type="Company",
        src_key="Acme",
        dst_type="Job",
        dst_key="j1",
        venture_id="v",
    )
    store.upsert_edges([e, e])
    assert len(store.edges(venture_id="v")) == 1


def test_knowledge_store_view_refresh_replaces_rows() -> None:
    store = InMemoryKnowledgeStore()
    store.refresh_view(MaterializedView(name="roles", venture_id="v", rows=[{"n": 1}]))
    store.refresh_view(MaterializedView(name="roles", venture_id="v", rows=[{"n": 2}, {"n": 3}]))
    view = store.get_view("roles", "v")
    assert view is not None and view.rows == [{"n": 2}, {"n": 3}]
    assert isinstance(view.refreshed_at, datetime)
    assert view.refreshed_at.tzinfo is UTC or view.refreshed_at.utcoffset() is not None
