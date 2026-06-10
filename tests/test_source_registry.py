"""Tests for ``source-registry``."""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.source_registry import SourceRegistry
from flywheel.persistence.source_store import InMemorySourceStore


def _runtime(tmp_path, node):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(node)
    return bus, runtime


def test_register_one_source_emits_sources_updated(tmp_path) -> None:
    store = InMemorySourceStore()
    node = SourceRegistry(store=store)
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("sources.updated", out.append)

    bus.publish(
        Event(
            type="source.register.requested",
            venture_id="postlineai",
            payload={"url": "https://api.example.com/jobs"},
        )
    )

    assert len(out) == 1
    assert out[0].payload["count"] == 1
    sources = store.list_enabled("postlineai")
    assert sources[0].url == "https://api.example.com/jobs"


def test_register_many_sources_in_one_event(tmp_path) -> None:
    store = InMemorySourceStore()
    node = SourceRegistry(store=store)
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("sources.updated", out.append)

    bus.publish(
        Event(
            type="source.register.requested",
            venture_id="v",
            payload={"sources": [{"url": "a"}, {"url": "b"}, {"url": "c"}]},
        )
    )
    assert out[0].payload["count"] == 3


def test_enrich_overrides_hints_and_can_disable(tmp_path) -> None:
    store = InMemorySourceStore()
    node = SourceRegistry(store=store)
    bus, _ = _runtime(tmp_path, node)

    bus.publish(
        Event(type="source.register.requested", venture_id="v", payload={"id": "s1", "url": "u"})
    )
    bus.publish(
        Event(
            type="source.enrich.requested",
            venture_id="v",
            payload={
                "source_id": "s1",
                "hints": {"id_field": "uuid"},
                "enrichment": {"sector": "saas"},
                "tags": ["ats"],
            },
        )
    )
    s = store.get("s1")
    assert s is not None
    assert s.hints == {"id_field": "uuid"}
    assert s.enrichment == {"sector": "saas"}
    assert s.tags == ["ats"]

    # Disabling removes it from the announced set.
    out: list[Event] = []
    bus.subscribe("sources.updated", out.append)
    bus.publish(
        Event(
            type="source.enrich.requested",
            venture_id="v",
            payload={"source_id": "s1", "enabled": False},
        )
    )
    assert out[-1].payload["count"] == 0
