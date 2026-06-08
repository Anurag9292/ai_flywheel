from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.slack_client import FakeSlackClient
from flywheel.nodes.human_review_queue import HumanReviewQueue


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def test_parks_human_gated_event_and_emits_nothing(tmp_path) -> None:
    slack = FakeSlackClient()
    queue = HumanReviewQueue(slack=slack)
    bus, _ = _runtime(tmp_path, queue)
    out: list[Event] = []
    bus.subscribe("post.approved", out.append)

    bus.publish(Event(
        type="post.drafted",
        venture_id="postlineai",
        payload={"customer_id": "c1", "draft": "[DRAFT NEEDED] ..."},
        tags={"requires_human": True},
    ))

    # Parked: nothing emitted yet, but the reviewer was pinged and it's pending.
    assert out == []
    assert len(slack.sent) == 1
    pending = queue.pending()
    assert len(pending) == 1
    assert pending[0]["type"] == "post.drafted"


def test_untagged_event_is_not_parked(tmp_path) -> None:
    queue = HumanReviewQueue()
    bus, _ = _runtime(tmp_path, queue)
    bus.publish(Event(
        type="post.drafted", venture_id="v", payload={"draft": "final"}
    ))
    assert queue.pending() == []


def test_approval_resumes_with_post_approved_same_correlation(tmp_path) -> None:
    queue = HumanReviewQueue()
    bus, _ = _runtime(tmp_path, queue)
    out: list[Event] = []
    bus.subscribe("post.approved", out.append)

    drafted = Event(
        type="post.drafted",
        venture_id="postlineai",
        payload={"customer_id": "c1", "draft": "placeholder"},
        tags={"requires_human": True},
    )
    bus.publish(drafted)
    assert out == []  # parked

    # Founder approves, writing the real text. Carries the parked event_id.
    bus.publish(Event(
        type="review.approved",
        venture_id="postlineai",
        correlation_id=drafted.correlation_id,
        payload={"event_id": drafted.event_id, "draft": "The real ghostwritten post."},
    ))

    assert len(out) == 1
    assert out[0].type == "post.approved"
    assert out[0].payload["draft"] == "The real ghostwritten post."
    assert out[0].payload["reviewed"] is True
    # The two runs are stitched by correlation id.
    assert out[0].correlation_id == drafted.correlation_id
    # Pending is cleared after approval.
    assert queue.pending() == []


def test_unknown_approval_is_noop(tmp_path) -> None:
    queue = HumanReviewQueue()
    bus, _ = _runtime(tmp_path, queue)
    out: list[Event] = []
    bus.subscribe("post.approved", out.append)
    bus.publish(Event(
        type="review.approved", venture_id="v", payload={"event_id": "does-not-exist"}
    ))
    assert out == []


def test_reacts_to_includes_review_and_parkable_types() -> None:
    queue = HumanReviewQueue()
    assert "review.approved" in queue.reacts_to
    assert "post.drafted" in queue.reacts_to
    assert "post.approved" in queue.emits
