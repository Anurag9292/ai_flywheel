from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.nodes.signal_analyzer import SignalAnalyzer, SignalVerdict
from flywheel.nodes.thesis_tracker import CONTRADICTED, SUPPORTED, ThesisTracker


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def _analyzer_returning(verdict: str) -> SignalAnalyzer:
    gw = FakeLLMGateway()
    gw.register(
        "SignalVerdict",
        lambda prompt: {"verdict": verdict, "confidence": 0.9, "explanation": "x"},
    )
    return SignalAnalyzer(gateway=gw)


def test_signal_analyzer_emits_verdict(tmp_path) -> None:
    analyzer = _analyzer_returning("strong")
    bus, _ = _runtime(tmp_path, analyzer)
    out: list[Event] = []
    bus.subscribe("signal.verdict", out.append)

    bus.publish(Event(
        type="campaign.metrics.updated",
        venture_id="postlineai",
        payload={"leads": 40, "signups": 18, "rubric": "would pay $499/mo"},
    ))

    assert len(out) == 1
    v = SignalVerdict.model_validate(out[0].payload)
    assert v.verdict == "strong"
    assert out[0].payload["signal_from"] == "campaign.metrics.updated"


def test_signal_analyzer_runs_with_defaults(tmp_path) -> None:
    analyzer = SignalAnalyzer()
    bus, _ = _runtime(tmp_path, analyzer)
    out: list[Event] = []
    bus.subscribe("signal.verdict", out.append)

    bus.publish(Event(type="campaign.metrics.updated", venture_id="v", payload={}))
    assert len(out) == 1
    SignalVerdict.model_validate(out[0].payload)  # default-filled (weak)


def test_same_node_reused_for_post_and_survey_signals(tmp_path) -> None:
    # Step-6 reuse: the SAME signal-analyzer judges product engagement and
    # survey signals, not just ad metrics — purely via new subscriptions.
    analyzer = _analyzer_returning("strong")
    assert "post.metrics.updated" in analyzer.reacts_to
    assert "survey.responded" in analyzer.reacts_to

    bus, _ = _runtime(tmp_path, analyzer)
    out: list[Event] = []
    bus.subscribe("signal.verdict", out.append)

    bus.publish(Event(
        type="post.metrics.updated",
        venture_id="postlineai",
        payload={"impressions": 5000, "reactions": 120, "rubric": "engagement up 2x"},
    ))
    bus.publish(Event(
        type="survey.responded",
        venture_id="postlineai",
        payload={"nps": 9, "rubric": "customers happy enough to renew"},
    ))

    assert [e.payload["signal_from"] for e in out] == [
        "post.metrics.updated",
        "survey.responded",
    ]


def test_verdict_feeds_thesis_tracker_strong_and_kill(tmp_path) -> None:
    tracker = ThesisTracker()
    bus, _ = _runtime(tmp_path, _analyzer_returning("strong"), tracker)
    bus.publish(Event(
        type="campaign.metrics.updated", venture_id="postlineai", payload={"leads": 50}
    ))
    assert tracker.state_for("postlineai").get("demand_validated") == SUPPORTED

    tracker2 = ThesisTracker()
    bus2, _ = _runtime(tmp_path, _analyzer_returning("kill"), tracker2)
    bus2.publish(Event(
        type="campaign.metrics.updated", venture_id="postlineai", payload={"leads": 0}
    ))
    assert tracker2.state_for("postlineai").get("demand_validated") == CONTRADICTED
