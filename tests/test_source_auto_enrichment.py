"""Tests for machine source enrichment in the registry (Phase 3)."""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.source_registry import SourceRegistry, infer_source_enrichment
from flywheel.persistence.source_store import InMemorySourceStore


def test_infer_enrichment_rules() -> None:
    assert infer_source_enrichment(
        "https://api.lever.co/v0/postings/acme"
    )["kind"] == "ats-job-board"
    assert infer_source_enrichment(
        "https://www.g2.com/products/acme/reviews"
    )["kind"] == "review-feed"
    assert infer_source_enrichment("https://example.com/data.json") == {}


def _registry():
    store = InMemorySourceStore()
    node = SourceRegistry(store=store)
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, keep_in_memory=True)
    runtime = Runtime(bus, recorder)
    runtime.register(node)
    return bus, store


def test_register_auto_enriches_kind_from_url() -> None:
    bus, store = _registry()
    bus.publish(
        Event(
            type="source.register.requested",
            venture_id="v1",
            payload={"url": "https://boards-api.greenhouse.io/v1/boards/x/jobs"},
        )
    )
    s = store.list_enabled("v1")[0]
    assert s.enrichment.get("kind") == "ats-job-board"
    assert "hiring-signal" in s.tags


def test_explicit_enrichment_is_not_clobbered() -> None:
    bus, store = _registry()
    bus.publish(
        Event(
            type="source.register.requested",
            venture_id="v1",
            payload={
                "url": "https://www.g2.com/products/x/reviews",
                "enrichment": {"kind": "custom-kind"},
            },
        )
    )
    s = store.list_enabled("v1")[0]
    # Caller-supplied kind wins over the inferred review-feed.
    assert s.enrichment["kind"] == "custom-kind"
