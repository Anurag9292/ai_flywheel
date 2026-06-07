from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.thesis_tracker import CONTRADICTED, SUPPORTED, ThesisTracker


def _runtime(tmp_path):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    tracker = ThesisTracker()
    runtime.register(tracker)
    return bus, tracker


def _evidence(assumption: str, supports: bool) -> Event:
    return Event(
        type="evidence.collected",
        venture_id="postlineai",
        payload={"assumption": assumption, "supports": supports},
    )


def test_supporting_evidence_marks_assumption_supported(tmp_path) -> None:
    bus, tracker = _runtime(tmp_path)
    bus.publish(_evidence("willing_to_pay_499", True))
    assert tracker.state_for("postlineai") == {"willing_to_pay_499": SUPPORTED}


def test_contradicting_evidence_marks_assumption_contradicted(tmp_path) -> None:
    bus, tracker = _runtime(tmp_path)
    bus.publish(_evidence("trusts_ai_voice", False))
    assert tracker.state_for("postlineai") == {"trusts_ai_voice": CONTRADICTED}


def test_node_emits_thesis_state_updated(tmp_path) -> None:
    bus, _ = _runtime(tmp_path)
    updates: list[Event] = []
    bus.subscribe("thesis.state.updated", updates.append)

    bus.publish(_evidence("willing_to_pay_499", True))

    assert len(updates) == 1
    assert updates[0].payload["assumption"] == "willing_to_pay_499"
    assert updates[0].payload["state"] == SUPPORTED


def test_evidence_without_assumption_is_a_noop(tmp_path) -> None:
    bus, tracker = _runtime(tmp_path)
    updates: list[Event] = []
    bus.subscribe("thesis.state.updated", updates.append)

    bus.publish(Event(type="evidence.collected", venture_id="postlineai", payload={}))

    assert updates == []
    assert tracker.state_for("postlineai") == {}


def test_emitted_event_inherits_correlation_id(tmp_path) -> None:
    bus, _ = _runtime(tmp_path)
    updates: list[Event] = []
    bus.subscribe("thesis.state.updated", updates.append)

    evidence = _evidence("willing_to_pay_499", True)
    bus.publish(evidence)

    assert updates[0].correlation_id == evidence.correlation_id


def test_reacts_to_market_landscape_as_evidence(tmp_path) -> None:
    # Reuse by subscription: a summarized landscape naming a gap supports the
    # 'market_gap_exists' assumption.
    bus, tracker = _runtime(tmp_path)
    updates: list[Event] = []
    bus.subscribe("thesis.state.updated", updates.append)

    bus.publish(Event(
        type="market.landscape.summarized",
        venture_id="postlineai",
        payload={"summary": "a clear gap exists at $499", "competitors": []},
    ))

    assert tracker.state_for("postlineai") == {"market_gap_exists": SUPPORTED}
    assert updates[0].payload["evidence_from"] == "market.landscape.summarized"


def test_signal_verdict_kill_contradicts(tmp_path) -> None:
    bus, tracker = _runtime(tmp_path)
    bus.publish(Event(
        type="signal.verdict",
        venture_id="postlineai",
        payload={"verdict": "kill"},
    ))
    assert tracker.state_for("postlineai") == {"demand_validated": CONTRADICTED}


def test_signal_verdict_weak_is_noop(tmp_path) -> None:
    bus, tracker = _runtime(tmp_path)
    updates: list[Event] = []
    bus.subscribe("thesis.state.updated", updates.append)
    bus.publish(Event(
        type="signal.verdict", venture_id="postlineai", payload={"verdict": "weak"}
    ))
    assert updates == []
    assert tracker.state_for("postlineai") == {}
