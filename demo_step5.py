"""End-to-end demo of PostlineAI Step 5 — Wizard-of-Oz (human-in-the-loop).

Run it:

    uv run python demo_step5.py

It reuses the dev ``build_runtime()`` (the same wiring the ``/topology`` UI
drives), then walks the Wizard-of-Oz product flow:

  Run 1: a customer's input is drafted by a *human* impl and PARKED in the
         human-review-queue (the synchronous chain ends — nothing more emits).
  ── the founder writes the real post (the "pause") ──
  Run 2: the founder approves (a separate ``review.approved`` event), the queue
         re-emits ``post.approved`` with the SAME correlation id, and the
         post-scheduler publishes it.

It also shows a subscription being activated + charged. Every hop is observed by
the trace-recorder automatically.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.core.events import Event
from flywheel.devserver.topology import build_runtime, find_review_queue

TRACE_LOG = Path("traces.jsonl")
VENTURE = "postlineai"


def _print_chain(recorder, correlation_id: str, title: str) -> None:
    rows = [t for t in recorder.traces if t["correlation_id"] == correlation_id]
    rows.sort(key=lambda r: r["captured_at"])
    print(f"\n{title}")
    if not rows:
        print("  (no reactions — chain ended / parked)")
    for i, t in enumerate(rows):
        arrow = "  " if i == 0 else "  ↳ "
        print(
            f"{arrow}{t['node']} v{t['node_version']} "
            f"(reacted to {t['trigger_type']}) emitted {t['emitted_types']}"
        )


def main() -> None:
    if TRACE_LOG.exists():
        TRACE_LOG.unlink()

    runtime, bus, recorder = build_runtime(TRACE_LOG, keep_in_memory=True)
    queue = find_review_queue(runtime)
    assert queue is not None

    # --- Run 1: customer input is drafted (human) and parked ----------------
    print("Run 1 — customer sends input (drafted by a human, parked for review)...")
    inbound = Event(
        type="inbound.received",
        venture_id=VENTURE,
        payload={
            "customer_id": "c1",
            "kind": "text",
            "content": "Want a post about why we moved off Kubernetes.",
        },
    )
    bus.publish(inbound)
    _print_chain(recorder, inbound.correlation_id, "Run 1 chain (ends at the parked review):")

    pending = queue.pending()
    print(f"\nParked for founder review: {len(pending)} item(s)")
    parked = pending[0]
    print(f"  event_id={parked['event_id'][:8]} draft={parked['payload'].get('draft')!r}")

    # --- Run 2: founder approves with the real text -> resume & publish -----
    print("\nRun 2 — founder writes the real post and approves...")
    approval = Event(
        type="review.approved",
        venture_id=VENTURE,
        correlation_id=parked["correlation_id"],  # same chain
        payload={
            "event_id": parked["event_id"],
            "draft": "Everyone said we were crazy to leave Kubernetes. Here's what happened…",
        },
    )
    bus.publish(approval)
    _print_chain(recorder, approval.correlation_id, "Run 2 chain (resumes -> publishes):")

    # --- A subscription, for good measure ------------------------------------
    print("\nSubscription — a trial customer signs up at $299...")
    sub = Event(
        type="subscription.requested",
        venture_id=VENTURE,
        payload={"customer_id": "c1", "plan": "trial", "amount_usd": 299},
    )
    bus.publish(sub)
    _print_chain(recorder, sub.correlation_id, "Subscription chain:")


if __name__ == "__main__":
    main()
