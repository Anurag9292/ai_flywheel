from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.linkedin_posting_client import (
    FakeLinkedInPostingClient,
    PostMetrics,
)
from flywheel.nodes.post_analytics_collector import PostAnalyticsCollector


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def test_collector_emits_metrics(tmp_path) -> None:
    posting = FakeLinkedInPostingClient(
        metrics={
            "li-post-1": PostMetrics(
                post_id="li-post-1", impressions=5000, reactions=120, comments=14, shares=6
            )
        }
    )
    bus, _ = _runtime(tmp_path, PostAnalyticsCollector(posting=posting))
    out: list[Event] = []
    bus.subscribe("post.metrics.updated", out.append)

    bus.publish(Event(
        type="post.published",
        venture_id="postlineai",
        payload={"post_id": "li-post-1", "customer_id": "c1"},
    ))

    assert len(out) == 1
    assert out[0].payload["impressions"] == 5000
    assert out[0].payload["customer_id"] == "c1"


def test_collector_noop_without_post_id(tmp_path) -> None:
    bus, _ = _runtime(tmp_path, PostAnalyticsCollector())
    out: list[Event] = []
    bus.subscribe("post.metrics.updated", out.append)
    bus.publish(Event(type="post.published", venture_id="v", payload={}))
    assert out == []


def test_collector_inherits_correlation_id(tmp_path) -> None:
    bus, _ = _runtime(tmp_path, PostAnalyticsCollector())
    out: list[Event] = []
    bus.subscribe("post.metrics.updated", out.append)
    trigger = Event(type="post.published", venture_id="v", payload={"post_id": "li-post-9"})
    bus.publish(trigger)
    assert out[0].correlation_id == trigger.correlation_id
