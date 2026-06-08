"""End-to-end demo of PostlineAI Step 3 + Step 4 — discovery & the decision loop.

Run it:

    uv run python demo_step3_4.py

It reuses the dev ``build_runtime()`` (the same wiring the ``/topology`` UI
drives) so the run is deterministic and offline, then publishes:

  1. ``transcript.captured`` — Step 3 discovery: ``pain-extractor`` extracts
     pains, which the existing ``thesis-tracker`` reacts to *by subscription*
     (no wiring change), which in turn notifies the founder.
  2. ``campaign.requested`` — Step 4 ad test: the full
     ``ad-campaign-runner → ad-analytics-collector → signal-analyzer →
     {thesis-tracker, founder-notifier}`` decision loop.

Every hop is observed by the trace-recorder automatically — nobody wires it.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.core.events import Event
from flywheel.devserver.topology import build_runtime

TRACE_LOG = Path("traces.jsonl")
VENTURE = "postlineai"


def _print_chain(recorder, correlation_id: str, title: str) -> None:
    rows = [t for t in recorder.traces if t["correlation_id"] == correlation_id]
    rows.sort(key=lambda r: r["captured_at"])
    print(f"\n{title}")
    for i, t in enumerate(rows):
        arrow = "  " if i == 0 else "  ↳ "
        print(
            f"{arrow}{t['node']} v{t['node_version']} "
            f"(reacted to {t['trigger_type']}) emitted {t['emitted_types']} "
            f"in {t['latency_ms']}ms"
        )


def main() -> None:
    if TRACE_LOG.exists():
        TRACE_LOG.unlink()

    runtime, bus, recorder = build_runtime(TRACE_LOG, keep_in_memory=True)

    # --- Step 3: a discovery call transcript arrives -------------------------
    print("Step 3 — publishing transcript.captured (a discovery call)...")
    t1 = Event(
        type="transcript.captured",
        venture_id=VENTURE,
        payload={
            "transcript": "I should post on LinkedIn but have no time, and my "
            "posts get no engagement when I do.",
            "speaker": "Founder A",
        },
    )
    bus.publish(t1)
    _print_chain(recorder, t1.correlation_id, "Step 3 chain:")

    # --- Step 4: run a $200 ad test ------------------------------------------
    print("\nStep 4 — publishing campaign.requested (a $200 LinkedIn ad test)...")
    t2 = Event(
        type="campaign.requested",
        venture_id=VENTURE,
        payload={
            "platform": "linkedin",
            "name": "ghostwriting waitlist",
            "budget_usd": 200,
            "landing_page": "/postlineai",
            "rubric": "would pay $499/mo",
        },
    )
    bus.publish(t2)
    _print_chain(recorder, t2.correlation_id, "Step 4 decision loop:")

    print("\nCode-derived topology lint (runtime.describe()['lint']):")
    print(json.dumps(runtime.describe()["lint"], indent=2))


if __name__ == "__main__":
    main()
