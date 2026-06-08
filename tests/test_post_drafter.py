from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.post_drafter import PostDrafter


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def test_human_drafter_emits_post_tagged_requires_human(tmp_path) -> None:
    drafter = PostDrafter()  # defaults to HumanDrafter
    bus, _ = _runtime(tmp_path, drafter)
    out: list[Event] = []
    bus.subscribe("post.drafted", out.append)

    bus.publish(Event(
        type="input.captured",
        venture_id="postlineai",
        payload={"customer_id": "c1", "text": "talk about hiring"},
    ))

    assert len(out) == 1
    assert out[0].tags.get("requires_human") is True
    assert "talk about hiring" in out[0].payload["draft"]
    assert out[0].payload["customer_id"] == "c1"


def test_human_binding_reflected_in_version_and_kind() -> None:
    node = PostDrafter()
    assert node.version == "0.1.0-human"
    assert node.kind == "dumb"


def test_agent_binding_does_not_require_human(tmp_path) -> None:
    # A stand-in agent drafter: produces final text, no human needed. Proves the
    # event interface is identical; only the binding changes (the Step-7 swap).
    class StubAgentDrafter:
        version = "agent-v1"

        def draft(self, customer_id: str, text: str) -> tuple[str, bool]:
            return f"Polished post about: {text}", False

    node = PostDrafter(drafter=StubAgentDrafter())
    assert node.version == "0.1.0-agent-v1"
    assert node.kind == "agentic"

    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("post.drafted", out.append)
    bus.publish(Event(
        type="input.captured", venture_id="v", payload={"customer_id": "c", "text": "x"}
    ))
    # No requires_human tag → flows straight on (no parking).
    assert out[0].tags.get("requires_human") is None
