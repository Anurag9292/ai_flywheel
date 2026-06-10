"""Tests for the ``insight-inferrer`` agentic node (Phase 2).

Uses the canned FakeLLMGateway wiring from the registry so the inference is
deterministic and offline.
"""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.persistence.knowledge_store import InMemoryKnowledgeStore
from flywheel.persistence.models import MaterializedView
from flywheel.venture.registry import build_node


def _runtime(tmp_path, node):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(node)
    return bus


def _seed_views(store: InMemoryKnowledgeStore, vid: str) -> None:
    store.refresh_view(
        MaterializedView(
            name="open_roles_by_company",
            venture_id=vid,
            rows=[{"company": "Acme", "open_roles": 2, "titles": ["Head of Content"]}],
        )
    )
    store.refresh_view(
        MaterializedView(
            name="recent_sentiment_by_company",
            venture_id=vid,
            rows=[
                {"company": "Acme", "total": 3, "negative": 3, "positive": 0,
                 "neutral": 0, "negative_ratio": 1.0},
                {"company": "BrightFern", "total": 2, "negative": 0, "positive": 2,
                 "neutral": 0, "negative_ratio": 0.0},
            ],
        )
    )


def test_insight_inferrer_emits_lead_and_risk(tmp_path) -> None:
    # The registry's canned wiring backs the node with a deterministic gateway;
    # but it reads the SHARED ingestion knowledge store, so seed that instead.
    from flywheel.venture.registry import reset_ingestion_stores

    bundle = reset_ingestion_stores()
    store = bundle.knowledge
    _seed_views(store, "postlineai")

    node = build_node("insight-inferrer", {})
    bus = _runtime(tmp_path, node)
    insights: list[Event] = []
    verdicts: list[Event] = []
    bus.subscribe("market.insight", insights.append)
    bus.subscribe("signal.verdict", verdicts.append)

    bus.publish(Event(type="knowledge.updated", venture_id="postlineai", payload={}))

    kinds = {e.payload["kind"] for e in insights}
    assert "lead_opportunity" in kinds
    assert "risk_signal" in kinds
    # A lead emits an urgent (strong) verdict; the negative-cluster risk too.
    companies_with_risk = {
        e.payload["company"] for e in insights if e.payload["kind"] == "risk_signal"
    }
    # Only the negative-cluster company is flagged as a risk (not BrightFern).
    assert "Acme" in companies_with_risk
    assert "BrightFern" not in companies_with_risk
    assert any(v.payload["verdict"] == "strong" for v in verdicts)


def test_insight_inferrer_noop_on_empty_graph(tmp_path) -> None:
    from flywheel.venture.registry import reset_ingestion_stores

    reset_ingestion_stores()  # empty knowledge store
    node = build_node("insight-inferrer", {})
    bus = _runtime(tmp_path, node)
    insights: list[Event] = []
    bus.subscribe("market.insight", insights.append)

    bus.publish(Event(type="knowledge.updated", venture_id="postlineai", payload={}))
    assert insights == []
