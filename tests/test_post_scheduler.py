from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.linkedin_posting_client import FakeLinkedInPostingClient
from flywheel.nodes.post_scheduler import PostScheduler


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def test_scheduler_schedules_then_publishes(tmp_path) -> None:
    posting = FakeLinkedInPostingClient()
    bus, _ = _runtime(tmp_path, PostScheduler(posting=posting))
    scheduled: list[Event] = []
    published: list[Event] = []
    bus.subscribe("post.scheduled", scheduled.append)
    bus.subscribe("post.published", published.append)

    bus.publish(Event(
        type="post.approved",
        venture_id="postlineai",
        payload={"customer_id": "c1", "draft": "The real post."},
    ))

    assert len(scheduled) == 1
    assert scheduled[0].payload["draft"] == "The real post."
    assert len(published) == 1
    assert published[0].payload["customer_id"] == "c1"
    assert "li-post-1" in published[0].payload["url"]
    assert len(posting.published) == 1


def test_scheduler_inherits_correlation_id(tmp_path) -> None:
    bus, _ = _runtime(tmp_path, PostScheduler())
    published: list[Event] = []
    bus.subscribe("post.published", published.append)
    trigger = Event(type="post.approved", venture_id="v", payload={"customer_id": "c"})
    bus.publish(trigger)
    assert published[0].correlation_id == trigger.correlation_id
