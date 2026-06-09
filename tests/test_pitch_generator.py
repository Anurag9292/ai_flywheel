"""Tests for ``pitch-generator``."""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.nodes.human_review_queue import HumanReviewQueue
from flywheel.nodes.pitch_generator import Pitch, PitchGenerator


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


def _canned_generator() -> PitchGenerator:
    gw = FakeLLMGateway()

    def _build(prompt: str) -> dict[str, object]:
        company = ""
        for line in prompt.splitlines():
            if line.startswith("Company: "):
                company = line[len("Company: ") :].strip()
                break
        return {
            "company": company,
            "contact_email": f"hello@{company.lower()}.example.com",
            "angle": f"angle for {company}",
            "email_subject": f"Subject for {company}",
            "email_body": f"Hi {company},\n\nLet's chat.",
            "linkedin_message": f"DM for {company}",
        }

    gw.register("Pitch", _build)
    return PitchGenerator(gateway=gw)


def test_emits_one_tagged_pitch_per_company(tmp_path) -> None:
    bus, _ = _runtime(tmp_path, _canned_generator())
    out: list[Event] = []
    bus.subscribe("pitch.drafted", out.append)

    bus.publish(
        Event(
            type="company.needs.profiled",
            venture_id="postlineai",
            payload={
                "offer": "$499/mo ghostwriting",
                "companies": [
                    {"company": "Acme", "top_need": "founder content"},
                    {"company": "Globex", "top_need": "thought leadership"},
                ],
            },
        )
    )

    assert len(out) == 2
    for event in out:
        assert event.type == "pitch.drafted"
        assert event.tags.get("requires_human") is True
        Pitch.model_validate(event.payload)
    assert {e.payload["company"] for e in out} == {"Acme", "Globex"}


def test_pitch_carries_email_through_when_agent_omits_it(tmp_path) -> None:
    gw = FakeLLMGateway()
    # Builder returns nothing for contact_email — node must fall back to the
    # company's pre-supplied email.
    gw.register(
        "Pitch",
        lambda prompt: {
            "company": "Acme",
            "angle": "x",
            "email_subject": "s",
            "email_body": "b",
            "linkedin_message": "m",
        },
    )
    bus, _ = _runtime(tmp_path, PitchGenerator(gateway=gw))
    out: list[Event] = []
    bus.subscribe("pitch.drafted", out.append)

    bus.publish(
        Event(
            type="company.needs.profiled",
            venture_id="v",
            payload={
                "companies": [
                    {"company": "Acme", "contact_email": "careers@acme.example.com"}
                ]
            },
        )
    )

    assert out[0].payload["contact_email"] == "careers@acme.example.com"


def test_pitch_drafted_parks_in_review_queue(tmp_path) -> None:
    # Wire pitch-generator → human-review-queue with the extended result_map
    # (pitch.drafted → pitch.approved). Pitches should park, not auto-resume.
    queue = HumanReviewQueue(
        result_map={"post.drafted": "post.approved", "pitch.drafted": "pitch.approved"}
    )
    bus, _ = _runtime(tmp_path, _canned_generator(), queue)

    approved: list[Event] = []
    bus.subscribe("pitch.approved", approved.append)
    drafted: list[Event] = []
    bus.subscribe("pitch.drafted", drafted.append)

    bus.publish(
        Event(
            type="company.needs.profiled",
            venture_id="postlineai",
            payload={"companies": [{"company": "Acme", "top_need": "x"}]},
        )
    )

    assert len(drafted) == 1  # the generator emitted
    assert approved == []  # queue parked, did NOT resume
    assert len(queue.pending()) == 1
    assert queue.pending()[0]["type"] == "pitch.drafted"


def test_review_approval_resumes_pitch_with_same_correlation(tmp_path) -> None:
    queue = HumanReviewQueue(
        result_map={"post.drafted": "post.approved", "pitch.drafted": "pitch.approved"}
    )
    bus, _ = _runtime(tmp_path, _canned_generator(), queue)
    approved: list[Event] = []
    bus.subscribe("pitch.approved", approved.append)

    trigger = Event(
        type="company.needs.profiled",
        venture_id="postlineai",
        payload={"companies": [{"company": "Acme"}]},
    )
    bus.publish(trigger)

    parked = queue.pending()[0]
    bus.publish(
        Event(
            type="review.approved",
            venture_id="postlineai",
            correlation_id=trigger.correlation_id,
            payload={
                "event_id": parked["event_id"],
                # Founder may overwrite the draft body at approval time. The
                # queue stores it in payload["draft"] (mirrors post-drafter).
                "draft": "Final, founder-edited pitch body.",
            },
        )
    )

    assert len(approved) == 1
    assert approved[0].type == "pitch.approved"
    assert approved[0].correlation_id == trigger.correlation_id
    assert approved[0].payload["company"] == "Acme"
    assert approved[0].payload["reviewed"] is True


def test_runs_with_defaults(tmp_path) -> None:
    # No injected gateway → falls back to FakeLLMGateway + Pitch defaults; the
    # node must still emit one tagged pitch.drafted per company.
    bus, _ = _runtime(tmp_path, PitchGenerator())
    out: list[Event] = []
    bus.subscribe("pitch.drafted", out.append)

    bus.publish(
        Event(
            type="company.needs.profiled",
            venture_id="v",
            payload={"companies": [{"company": "Acme"}]},
        )
    )

    assert len(out) == 1
    assert out[0].tags.get("requires_human") is True
