"""Tests for ``knowledge-builder`` — incremental, generic extraction, views."""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.knowledge_builder import KnowledgeBuilder
from flywheel.persistence.knowledge_store import InMemoryKnowledgeStore
from flywheel.persistence.models import RawRecord
from flywheel.persistence.raw_record_store import InMemoryRawRecordStore


def _runtime(tmp_path, node):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(node)
    return bus, runtime


def _seed(raw: InMemoryRawRecordStore, recs: list[dict]) -> None:
    raw.upsert_many(
        [
            RawRecord(
                source_id=r.get("source_id", "s"),
                venture_id="v",
                external_id=r["external_id"],
                raw=r["raw"],
            )
            for r in recs
        ]
    )


def test_builds_entities_edges_and_views(tmp_path) -> None:
    raw = InMemoryRawRecordStore()
    knowledge = InMemoryKnowledgeStore()
    _seed(
        raw,
        [
            {
                "external_id": "1",
                "raw": {
                    "id": "1",
                    "title": "Head of Content",
                    "company": "Acme",
                    "department": "Marketing",
                    "location": "Remote",
                },
            },
            {
                "external_id": "2",
                "raw": {
                    "id": "2",
                    "title": "Brand Lead",
                    "company": "Acme",
                    "department": "Marketing",
                },
            },
        ],
    )
    node = KnowledgeBuilder(raw_store=raw, knowledge_store=knowledge)
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("knowledge.updated", out.append)

    bus.publish(Event(type="source.records.ingested", venture_id="v", payload={"source_id": "s"}))

    assert out[0].payload["new_records"] == 2
    jobs = knowledge.entities(type="Job", venture_id="v")
    assert len(jobs) == 2
    companies = knowledge.entities(type="Company", venture_id="v")
    assert [c.key for c in companies] == ["Acme"]
    # Edge: company posts job.
    posts = knowledge.edges(type="posts", venture_id="v")
    assert len(posts) == 2

    view = knowledge.get_view("open_roles_by_company", "v")
    assert view is not None
    assert view.rows == [
        {"company": "Acme", "open_roles": 2, "titles": ["Brand Lead", "Head of Content"]}
    ]


def test_incremental_only_processes_new_records(tmp_path) -> None:
    raw = InMemoryRawRecordStore()
    knowledge = InMemoryKnowledgeStore()
    node = KnowledgeBuilder(raw_store=raw, knowledge_store=knowledge)
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("knowledge.updated", out.append)

    _seed(raw, [{"external_id": "1", "raw": {"id": "1", "title": "A", "company": "Acme"}}])
    bus.publish(Event(type="source.records.ingested", venture_id="v", payload={}))
    assert out[0].payload["new_records"] == 1

    # Add one more; the builder must process ONLY the new record.
    _seed(raw, [{"external_id": "2", "raw": {"id": "2", "title": "B", "company": "Acme"}}])
    bus.publish(Event(type="tick.daily", venture_id="v", payload={}))
    assert out[1].payload["new_records"] == 1
    assert out[1].payload["watermark"] == 2


def test_no_new_records_emits_nothing(tmp_path) -> None:
    raw = InMemoryRawRecordStore()
    node = KnowledgeBuilder(raw_store=raw, knowledge_store=InMemoryKnowledgeStore())
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("knowledge.updated", out.append)
    bus.publish(Event(type="tick.daily", venture_id="v", payload={}))
    assert out == []


def test_generic_extraction_handles_nested_and_alias_fields(tmp_path) -> None:
    # No "title"/"company" keys: uses "text" alias + nested categories.dept.
    raw = InMemoryRawRecordStore()
    knowledge = InMemoryKnowledgeStore()
    _seed(
        raw,
        [
            {
                "external_id": "x",
                "raw": {
                    "id": "x",
                    "text": "Engineer",
                    "_company": "Northwind",
                    "categories": {"department": "Engineering", "location": "Berlin"},
                },
            }
        ],
    )
    node = KnowledgeBuilder(raw_store=raw, knowledge_store=knowledge)
    bus, _ = _runtime(tmp_path, node)
    bus.publish(Event(type="source.records.ingested", venture_id="v", payload={}))

    job = knowledge.entities(type="Job", venture_id="v")[0]
    assert job.props["title"] == "Engineer"
    assert job.props["company"] == "Northwind"
    assert job.props["department"] == "Engineering"
    assert job.props["location"] == "Berlin"
