from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.nodes.pain_extractor import PainExtractor, PainReport
from flywheel.nodes.thesis_tracker import SUPPORTED, ThesisTracker


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def _extractor_with_canned_report() -> PainExtractor:
    gw = FakeLLMGateway()
    gw.register(
        "PainReport",
        lambda prompt: {
            "pains": [
                {"pain": "no time to write", "frequency": 7, "intensity": 0.8},
                {"pain": "posts get no engagement", "frequency": 4, "intensity": 0.6},
            ]
        },
    )
    return PainExtractor(gateway=gw)


def test_pain_extractor_emits_structured_report(tmp_path) -> None:
    extractor = _extractor_with_canned_report()
    bus, _ = _runtime(tmp_path, extractor)
    out: list[Event] = []
    bus.subscribe("pain.extracted", out.append)

    bus.publish(Event(
        type="transcript.captured",
        venture_id="postlineai",
        payload={"transcript": "I have no time and posts flop", "speaker": "Founder A"},
    ))

    assert len(out) == 1
    report = PainReport.model_validate(out[0].payload)
    assert report.pains[0].pain == "no time to write"
    assert report.pains[0].frequency == 7


def test_pain_extractor_inherits_correlation_id(tmp_path) -> None:
    extractor = _extractor_with_canned_report()
    bus, _ = _runtime(tmp_path, extractor)
    out: list[Event] = []
    bus.subscribe("pain.extracted", out.append)

    trigger = Event(type="transcript.captured", venture_id="postlineai", payload={})
    bus.publish(trigger)

    assert out[0].correlation_id == trigger.correlation_id


def test_pain_extractor_runs_with_defaults(tmp_path) -> None:
    # No injected gateway: uses fake; falls back to PainReport defaults (empty).
    extractor = PainExtractor()
    bus, _ = _runtime(tmp_path, extractor)
    out: list[Event] = []
    bus.subscribe("pain.extracted", out.append)

    bus.publish(Event(type="transcript.captured", venture_id="v", payload={}))

    assert len(out) == 1
    PainReport.model_validate(out[0].payload)  # valid, default-filled


def test_pain_extracted_feeds_thesis_tracker_by_subscription(tmp_path) -> None:
    """The Step-3 reuse payoff: pain-extractor -> thesis-tracker, no wiring change."""
    extractor = _extractor_with_canned_report()
    tracker = ThesisTracker()
    bus, _ = _runtime(tmp_path, extractor, tracker)

    bus.publish(Event(
        type="transcript.captured",
        venture_id="postlineai",
        payload={"transcript": "pain pain pain"},
    ))

    assert tracker.state_for("postlineai").get("problem_is_real") == SUPPORTED
