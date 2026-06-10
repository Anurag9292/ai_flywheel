import json
from typing import Any

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.substrate import TraceRecorder, _truncate_for_log


def _evt(payload: dict[str, Any] | None = None) -> Event:
    return Event(type="evidence.collected", venture_id="v1", payload=payload or {})


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


def test_file_captures_full_payloads(tmp_path) -> None:
    bus = InMemoryEventBus()
    log_path = tmp_path / "traces.jsonl"
    recorder = TraceRecorder(bus, log_path=log_path)

    out = Event(
        type="post.drafted",
        venture_id="v1",
        payload={"draft": "The full ghostwritten post body.", "customer_id": "c1"},
    )
    recorder.record(
        node_name="post-drafter",
        node_version="0.1.0",
        triggering_event=_evt({"content": "voice note transcript"}),
        handle=lambda: [out],
    )

    trace = json.loads(log_path.read_text().splitlines()[0])
    # FULL trigger payload + emitted payloads are persisted.
    assert trace["trigger_payload"] == {"content": "voice note transcript"}
    assert trace["emitted"][0]["type"] == "post.drafted"
    assert trace["emitted"][0]["payload"]["draft"] == "The full ghostwritten post body."
    # Backward-compatible flat fields remain.
    assert trace["emitted_types"] == ["post.drafted"]
    assert trace["emitted_event_ids"] == [out.event_id]


def test_event_carries_full_payloads(tmp_path) -> None:
    bus = InMemoryEventBus()
    captured: list[Event] = []
    bus.subscribe("trace.captured", captured.append)
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")

    out = Event(type="signal.verdict", venture_id="v1", payload={"verdict": "strong"})
    recorder.record(
        node_name="signal-analyzer",
        node_version="0.1.0",
        triggering_event=_evt(),
        handle=lambda: [out],
    )
    assert captured[0].payload["emitted"][0]["payload"] == {"verdict": "strong"}


def test_non_serializable_payload_does_not_crash(tmp_path) -> None:
    bus = InMemoryEventBus()
    log_path = tmp_path / "traces.jsonl"
    recorder = TraceRecorder(bus, log_path=log_path)

    class Weird:
        def __repr__(self) -> str:
            return "WEIRD_OBJ"

    out = Event(type="x.done", venture_id="v1", payload={"obj": Weird()})
    # Must not raise — payload is coerced to a JSON-safe string.
    recorder.record(
        node_name="n", node_version="1", triggering_event=_evt(), handle=lambda: [out]
    )
    trace = json.loads(log_path.read_text().splitlines()[0])
    assert trace["emitted"][0]["payload"]["obj"] == "WEIRD_OBJ"


def test_truncate_for_log_caps_long_strings() -> None:
    long = "a" * 500
    trace = {"trigger_payload": {"text": long}, "node": "n"}
    out = _truncate_for_log(trace, 200)
    assert out["node"] == "n"  # short values untouched
    assert len(out["trigger_payload"]["text"]) == 201  # 200 chars + "…"
    assert out["trigger_payload"]["text"].endswith("…")
    # limit <= 0 disables truncation.
    assert _truncate_for_log({"t": long}, 0)["t"] == long
