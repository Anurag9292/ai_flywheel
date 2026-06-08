from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.email_client import FakeEmailClient
from flywheel.libraries.slack_client import FakeSlackClient
from flywheel.nodes.founder_notifier import FounderNotifier


def _runtime(tmp_path, node):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(node)
    return bus, runtime


def test_strong_verdict_is_urgent_slack_and_email(tmp_path) -> None:
    slack, email = FakeSlackClient(), FakeEmailClient()
    notifier = FounderNotifier(slack=slack, email=email)
    bus, _ = _runtime(tmp_path, notifier)
    out: list[Event] = []
    bus.subscribe("founder.notified", out.append)

    bus.publish(Event(
        type="signal.verdict",
        venture_id="postlineai",
        payload={"verdict": "strong", "confidence": 0.9, "explanation": "good"},
    ))

    assert len(slack.sent) == 1
    assert len(email.sent) == 1
    assert out[0].payload["urgent"] is True
    assert set(out[0].payload["via"]) == {"slack", "email"}


def test_weak_verdict_is_email_only(tmp_path) -> None:
    slack, email = FakeSlackClient(), FakeEmailClient()
    notifier = FounderNotifier(slack=slack, email=email)
    bus, _ = _runtime(tmp_path, notifier)

    bus.publish(Event(
        type="signal.verdict", venture_id="v", payload={"verdict": "weak"}
    ))

    assert slack.sent == []
    assert len(email.sent) == 1


def test_thesis_update_notifies_via_email(tmp_path) -> None:
    slack, email = FakeSlackClient(), FakeEmailClient()
    notifier = FounderNotifier(slack=slack, email=email)
    bus, _ = _runtime(tmp_path, notifier)
    out: list[Event] = []
    bus.subscribe("founder.notified", out.append)

    bus.publish(Event(
        type="thesis.state.updated",
        venture_id="v",
        payload={"assumption": "demand_validated", "state": "supported"},
    ))

    assert len(email.sent) == 1
    assert out[0].payload["urgent"] is False


def test_urgent_tag_forces_slack(tmp_path) -> None:
    slack, email = FakeSlackClient(), FakeEmailClient()
    notifier = FounderNotifier(slack=slack, email=email)
    bus, _ = _runtime(tmp_path, notifier)

    bus.publish(Event(
        type="thesis.state.updated",
        venture_id="v",
        payload={"assumption": "x", "state": "contradicted"},
        tags={"urgent": True},
    ))

    assert len(slack.sent) == 1
