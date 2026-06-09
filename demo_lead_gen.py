"""End-to-end demo of PostlineAI's outbound lead-gen loop.

Run it:

    uv run python demo_lead_gen.py

It reuses the dev ``build_runtime()`` (the same wiring the ``/topology`` UI
drives), then walks the outbound chain:

  Run 1: ``lead-search.requested`` → ``lead-sourcer`` finds companies hiring
         for content/brand/founder roles → ``company-needs-analyzer`` infers
         each company's top need → ``pitch-generator`` drafts an email + a
         LinkedIn DM per company → each ``pitch.drafted`` is PARKED in the
         human-review-queue (the synchronous chain ends — nothing more emits).
  ── the founder reviews the parked pitches (the "pause") ──
  Run 2: the founder approves the first pitch (a separate ``review.approved``
         event); the queue re-emits ``pitch.approved`` with the SAME
         correlation id, stitching the two runs in the trace timeline.

Every hop is observed by the trace-recorder automatically. The same
``human-review-queue`` that parks ``post.drafted`` (Step 5) now also parks
``pitch.drafted`` — registry-time wiring, zero node-code changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flywheel.env import load_dotenv_if_present

# Pick up a repo-root .env so a `FLYWHEEL_VENTURE=postlineai-live` demo run finds
# its keys. No-op for the default (fake) venture, which needs none.
load_dotenv_if_present()

from flywheel.core.events import Event  # noqa: E402
from flywheel.devserver.topology import build_runtime, find_review_queue  # noqa: E402

TRACE_LOG = Path("traces.jsonl")
VENTURE = "postlineai"


def _print_chain(recorder: Any, correlation_id: str, title: str) -> None:
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


def _print_pitch(idx: int, item: dict[str, Any]) -> None:
    pl = item["payload"]
    company = pl.get("company", "?")
    email = pl.get("contact_email") or "(no email — LinkedIn-only)"
    print(f"  [{idx}] {company}  →  {email}")
    if pl.get("angle"):
        print(f"        angle    : {pl['angle']}")
    if pl.get("email_subject"):
        print(f"        subject  : {pl['email_subject']}")
    if pl.get("email_body"):
        body = pl["email_body"].splitlines()[0][:90]
        print(f"        email[0] : {body}…")
    if pl.get("linkedin_message"):
        print(f"        linkedin : {pl['linkedin_message'][:90]}…")


def main() -> None:
    if TRACE_LOG.exists():
        TRACE_LOG.unlink()

    runtime, bus, recorder = build_runtime(TRACE_LOG, keep_in_memory=True)
    queue = find_review_queue(runtime)
    assert queue is not None

    # --- Run 1: trigger the outbound chain → 3 parked pitches ----------------
    print(
        "Run 1 — searching for companies hiring for content / brand / founder "
        "roles, inferring needs, drafting tailored email + LinkedIn pitches…"
    )
    trigger = Event(
        type="lead-search.requested",
        venture_id=VENTURE,
        # Empty payload → the registry's canned default criteria are used
        # (PostlineAI ICP: marketing/content/founder-comms keywords).
        payload={},
    )
    bus.publish(trigger)
    _print_chain(
        recorder,
        trigger.correlation_id,
        "Run 1 chain (ends at the parked pitches):",
    )

    pending = [p for p in queue.pending() if p["type"] == "pitch.drafted"]
    print(f"\nParked for founder review: {len(pending)} pitch(es)")
    for i, item in enumerate(pending, start=1):
        _print_pitch(i, item)

    if not pending:
        print("  (none parked — check your venture wiring)")
        return

    # --- Run 2: founder approves the first pitch -> resume -------------------
    parked = pending[0]
    print(
        f"\nRun 2 — founder approves the {parked['payload'].get('company','?')} "
        "pitch (optionally editing the body)…"
    )
    approval = Event(
        type="review.approved",
        venture_id=VENTURE,
        correlation_id=parked["correlation_id"],  # same chain
        payload={
            "event_id": parked["event_id"],
            "draft": (
                f"Hi {parked['payload'].get('company','team')} — quick note "
                "from the PostlineAI founder. Saw you're hiring for content; "
                "we ghostwrite the founder's LinkedIn from week one. Worth a "
                "15-minute chat?"
            ),
        },
    )
    bus.publish(approval)
    _print_chain(
        recorder,
        approval.correlation_id,
        "Run 2 chain (resumes → pitch.approved emitted):",
    )

    remaining = [p for p in queue.pending() if p["type"] == "pitch.drafted"]
    print(
        f"\nStill parked after this approval: {len(remaining)} pitch(es) "
        "(approve them in the /topology UI to send them next)."
    )


if __name__ == "__main__":
    main()
