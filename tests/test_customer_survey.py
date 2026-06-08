from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.email_client import FakeEmailClient
from flywheel.libraries.slack_client import FakeSlackClient
from flywheel.nodes.customer_survey import CustomerSurvey


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def test_survey_sends_email_and_emits_response(tmp_path) -> None:
    email = FakeEmailClient()
    bus, _ = _runtime(tmp_path, CustomerSurvey(email=email))
    out: list[Event] = []
    bus.subscribe("survey.responded", out.append)

    bus.publish(Event(
        type="survey.requested",
        venture_id="postlineai",
        payload={"customer_id": "c1", "nps": 10, "leads": 2},
    ))

    assert len(email.sent) == 1
    assert len(out) == 1
    assert out[0].payload["nps"] == 10
    assert out[0].payload["leads"] == 2


def test_survey_slack_channel(tmp_path) -> None:
    slack = FakeSlackClient()
    bus, _ = _runtime(tmp_path, CustomerSurvey(slack=slack))
    bus.publish(Event(
        type="survey.requested",
        venture_id="v",
        payload={"customer_id": "c1", "channel": "slack", "to": "#dm"},
    ))
    assert len(slack.sent) == 1


def test_survey_inherits_correlation_id(tmp_path) -> None:
    bus, _ = _runtime(tmp_path, CustomerSurvey())
    out: list[Event] = []
    bus.subscribe("survey.responded", out.append)
    trigger = Event(type="survey.requested", venture_id="v", payload={"customer_id": "c"})
    bus.publish(trigger)
    assert out[0].correlation_id == trigger.correlation_id
