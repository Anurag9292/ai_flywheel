"""End-to-end demo of the Layer 1 substrate (PostlineAI Step 1).

Run it:

    uv run python demo.py

It wires up the in-memory bus, the trace-recorder, and the ``thesis-tracker``
node, then publishes two ``evidence.collected`` events. You should see:

  1. the node react and emit ``thesis.state.updated`` (event-driven flow), and
  2. a ``traces.jsonl`` file with one ``trace.captured`` row per node run
     (automatic observability — nobody wired it).

That single run proves both halves of the architecture: events flow between
capabilities, and every capability call is observed for free.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.core import Event, InMemoryEventBus, Runtime, TraceRecorder
from flywheel.nodes.thesis_tracker import ThesisTracker

TRACE_LOG = Path("traces.jsonl")
VENTURE = "postlineai"


def main() -> None:
    if TRACE_LOG.exists():
        TRACE_LOG.unlink()

    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=TRACE_LOG)
    runtime = Runtime(bus, recorder)

    tracker = ThesisTracker()
    runtime.register(tracker)

    # An observer that just prints the result events the node emits, so we can
    # *see* the event-driven flow. This is also exactly how Layer 3 attaches:
    # subscribe and watch, never call.
    def watch(event: Event) -> None:
        print(f"  ↳ emitted {event.type}: {event.payload.get('assumption')} "
              f"= {event.payload.get('state')}")

    bus.subscribe("thesis.state.updated", watch)

    print("Publishing evidence about PostlineAI's riskiest assumptions...\n")

    print("Evidence 1: ad test shows people will pay $499/mo (supports)")
    bus.publish(Event(
        type="evidence.collected",
        venture_id=VENTURE,
        payload={"assumption": "willing_to_pay_499", "supports": True},
    ))

    print("\nEvidence 2: interviews suggest founders won't trust an AI voice (contradicts)")
    bus.publish(Event(
        type="evidence.collected",
        venture_id=VENTURE,
        payload={"assumption": "trusts_ai_voice", "supports": False},
    ))

    print("\nFinal tracked thesis state:")
    for assumption, state in tracker.state_for(VENTURE).items():
        print(f"  - {assumption}: {state}")

    print(f"\nAutomatic traces written to {TRACE_LOG} (nobody wired this):")
    for line in TRACE_LOG.read_text().splitlines():
        t = json.loads(line)
        print(f"  - {t['node']} v{t['node_version']} reacted to {t['trigger_type']} "
              f"in {t['latency_ms']}ms, emitted {t['emitted_types']}")


if __name__ == "__main__":
    main()
