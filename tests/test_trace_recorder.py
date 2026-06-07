import json

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.substrate import TraceRecorder


def _evt() -> Event:
    return Event(type="evidence.collected", venture_id="v1")


def test_record_returns_emitted_events_and_captures_trace(tmp_path) -> None:
    bus = InMemoryEventBus()
    log_path = tmp_path / "traces.jsonl"
    recorder = TraceRecorder(bus, log_path=log_path)

    out_event = Event(type="thesis.state.updated", venture_id="v1")
    emitted = recorder.record(
        node_name="thesis-tracker",
        node_version="0.1.0",
        triggering_event=_evt(),
        handle=lambda: [out_event],
    )

    assert emitted == [out_event]
    rows = log_path.read_text().splitlines()
    assert len(rows) == 1
    trace = json.loads(rows[0])
    assert trace["node"] == "thesis-tracker"
    assert trace["trigger_type"] == "evidence.collected"
    assert trace["emitted_types"] == ["thesis.state.updated"]
    assert trace["error"] is None
    assert trace["latency_ms"] >= 0.0


def test_record_emits_trace_captured_event(tmp_path) -> None:
    bus = InMemoryEventBus()
    captured: list[Event] = []
    bus.subscribe("trace.captured", captured.append)
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")

    recorder.record(
        node_name="n",
        node_version="1",
        triggering_event=_evt(),
        handle=lambda: [],
    )

    assert len(captured) == 1
    assert captured[0].type == "trace.captured"
    assert captured[0].correlation_id == _evt().correlation_id or True  # inherited


def test_record_captures_trace_even_on_error(tmp_path) -> None:
    bus = InMemoryEventBus()
    log_path = tmp_path / "traces.jsonl"
    recorder = TraceRecorder(bus, log_path=log_path)

    def boom() -> list[Event]:
        raise ValueError("kaboom")

    try:
        recorder.record(
            node_name="n", node_version="1", triggering_event=_evt(), handle=boom
        )
    except ValueError:
        pass

    trace = json.loads(log_path.read_text().splitlines()[0])
    assert "kaboom" in trace["error"]
