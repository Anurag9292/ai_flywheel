"""End-to-end demo of PostlineAI Step 6 — measure what's working.

Run it:

    uv run python demo_step6.py

It reuses the dev ``build_runtime()`` and shows the two Step-6 capabilities, and
— crucially — that the SAME ``signal-analyzer`` from Step 4 now judges product
engagement and survey signals too, purely by subscription (no new code):

  1. A published post (we emit ``post.published`` directly) flows into
     ``post-analytics-collector → post.metrics.updated → signal-analyzer →
     signal.verdict → {thesis-tracker, founder-notifier}``.
  2. A ``survey.requested`` runs ``customer-survey → survey.responded``, which
     fans out to BOTH ``signal-analyzer`` and ``thesis-tracker``.

The reuse of signal-analyzer across ad / engagement / survey signals is the
payoff the walkthrough predicts for Step 6.
"""

from __future__ import annotations

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
            f"(reacted to {t['trigger_type']}) emitted {t['emitted_types']}"
        )


def main() -> None:
    if TRACE_LOG.exists():
        TRACE_LOG.unlink()

    _runtime, bus, recorder = build_runtime(TRACE_LOG, keep_in_memory=True)

    # 1) A published post → engagement analytics → signal (reused) → thesis/founder.
    print("Post published → measure engagement (analytics → signal-analyzer reuse)...")
    pub = Event(
        type="post.published",
        venture_id=VENTURE,
        payload={
            "post_id": "li-post-1",
            "customer_id": "c1",
            "rubric": "engagement up vs. baseline; worth renewing",
        },
    )
    bus.publish(pub)
    _print_chain(recorder, pub.correlation_id, "Engagement chain:")

    # 2) An NPS survey → response → signal (reused) + thesis.
    print("\nNPS survey → response → signal-analyzer (reused) + thesis-tracker...")
    survey = Event(
        type="survey.requested",
        venture_id=VENTURE,
        payload={"customer_id": "c1", "nps": 9, "leads": 2, "rubric": "happy to renew?"},
    )
    bus.publish(survey)
    _print_chain(recorder, survey.correlation_id, "Survey chain:")


if __name__ == "__main__":
    main()
