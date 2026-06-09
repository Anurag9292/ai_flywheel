"""End-to-end integration test for the outbound lead-gen flow.

Exercises the full chain through the *venture-loaded* runtime (not a hand-wired
one) so we prove that:

  1. The new ``lead-generation`` function in ``ventures/postlineai.yaml`` loads
     and registers the three new nodes via the registry's canned factories.
  2. ``lead-search.requested`` propagates through:
        lead-sourcer → companies.discovered
        company-needs-analyzer → company.needs.profiled
        pitch-generator → pitch.drafted (tagged requires_human)
        human-review-queue → (parked, no further emission)
  3. On a separate ``review.approved`` (run 2), the queue re-emits
     ``pitch.approved`` under the same ``correlation_id`` — the park-and-resume
     pattern, identical to ``post-drafter``.
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.devserver.topology import build_runtime, find_review_queue


def test_lead_gen_chain_through_venture_runtime(tmp_path) -> None:
    runtime, bus, _recorder = build_runtime(trace_log=tmp_path / "t.jsonl")
    registered = {n.name for n in runtime.nodes}
    # The new nodes registered (proves the venture file loaded them).
    assert "lead-sourcer" in registered
    assert "company-needs-analyzer" in registered
    assert "pitch-generator" in registered
    assert "human-review-queue" in registered

    drafted: list[Event] = []
    profiled: list[Event] = []
    discovered: list[Event] = []
    approved: list[Event] = []
    bus.subscribe("companies.discovered", discovered.append)
    bus.subscribe("company.needs.profiled", profiled.append)
    bus.subscribe("pitch.drafted", drafted.append)
    bus.subscribe("pitch.approved", approved.append)

    # Run 1: trigger the chain.
    trigger = Event(
        type="lead-search.requested",
        venture_id="postlineai",
        payload={},  # empty → registry-supplied default criteria are used
    )
    bus.publish(trigger)

    # Each step emitted at least once and shares the same correlation id.
    assert len(discovered) == 1
    assert len(profiled) == 1
    assert len(drafted) >= 1
    for event in (discovered[0], profiled[0], *drafted):
        assert event.correlation_id == trigger.correlation_id

    # Pitches were *parked* — none should have auto-approved.
    assert approved == []

    queue = find_review_queue(runtime)
    assert queue is not None
    pending = queue.pending()
    pitch_pending = [p for p in pending if p["type"] == "pitch.drafted"]
    assert len(pitch_pending) == len(drafted)

    # Every parked pitch carries through company + email payload to the reviewer.
    for item in pitch_pending:
        assert "company" in item["payload"]
        assert "email_body" in item["payload"]
        assert "linkedin_message" in item["payload"]


def test_lead_gen_park_and_resume_stitches_correlation_id(tmp_path) -> None:
    runtime, bus, _ = build_runtime(trace_log=tmp_path / "t.jsonl")
    queue = find_review_queue(runtime)
    assert queue is not None

    approved: list[Event] = []
    bus.subscribe("pitch.approved", approved.append)

    trigger = Event(type="lead-search.requested", venture_id="postlineai", payload={})
    bus.publish(trigger)

    # Approve the first parked pitch.
    pending = [p for p in queue.pending() if p["type"] == "pitch.drafted"]
    assert pending, "expected at least one parked pitch"
    parked = pending[0]

    # Run 2: founder approves; the queue must re-emit pitch.approved under the
    # same correlation id so the trace timeline stitches the two runs.
    bus.publish(
        Event(
            type="review.approved",
            venture_id="postlineai",
            correlation_id=trigger.correlation_id,
            payload={
                "event_id": parked["event_id"],
                "draft": "Final founder-edited outreach body.",
            },
        )
    )

    matching = [e for e in approved if e.correlation_id == trigger.correlation_id]
    assert len(matching) == 1
    assert matching[0].type == "pitch.approved"
    assert matching[0].payload["reviewed"] is True
    assert matching[0].payload["draft"] == "Final founder-edited outreach body."
    # Approved item is no longer pending.
    remaining_ids = {p["event_id"] for p in queue.pending()}
    assert parked["event_id"] not in remaining_ids
