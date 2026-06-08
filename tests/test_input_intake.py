from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.transcription_client import FakeTranscriptionClient
from flywheel.nodes.input_intake import InputIntake


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def test_text_input_passes_through(tmp_path) -> None:
    bus, _ = _runtime(tmp_path, InputIntake())
    out: list[Event] = []
    bus.subscribe("input.captured", out.append)

    bus.publish(Event(
        type="inbound.received",
        venture_id="postlineai",
        payload={"customer_id": "c1", "kind": "text", "content": "bullet points here"},
    ))

    assert len(out) == 1
    assert out[0].payload == {"customer_id": "c1", "text": "bullet points here"}


def test_audio_input_is_transcribed(tmp_path) -> None:
    intake = InputIntake(
        transcription=FakeTranscriptionClient(fixtures={"rec-1": "spoken words"})
    )
    bus, _ = _runtime(tmp_path, intake)
    out: list[Event] = []
    bus.subscribe("input.captured", out.append)

    bus.publish(Event(
        type="inbound.received",
        venture_id="postlineai",
        payload={"customer_id": "c2", "kind": "audio", "content": "rec-1"},
    ))

    assert out[0].payload["text"] == "spoken words"


def test_inherits_correlation_id(tmp_path) -> None:
    bus, _ = _runtime(tmp_path, InputIntake())
    out: list[Event] = []
    bus.subscribe("input.captured", out.append)
    trigger = Event(type="inbound.received", venture_id="v", payload={})
    bus.publish(trigger)
    assert out[0].correlation_id == trigger.correlation_id
