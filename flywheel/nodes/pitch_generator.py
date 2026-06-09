"""``pitch-generator`` — derived in PostlineAI's outbound lead-gen step.

> *The venture needs to: turn each company's inferred top need into a tailored
> outreach pitch — short email body **and** a LinkedIn DM variant — that opens
> with the angle and ends with a clear ask.*

An **event-driven node** (agentic) that reacts to ``company.needs.profiled``
and emits **one ``pitch.drafted`` event per company**, each tagged
``requires_human=true`` so it parks in the existing
:class:`~flywheel.nodes.human_review_queue.HumanReviewQueue` for founder
approval. On approval the queue re-emits ``pitch.approved`` (same correlation
id), which ``founder-notifier`` is wired to surface.

- **Reacts to:** ``company.needs.profiled``.
- **Calls:** ``llm-gateway`` (via its ``Agent``).
- **Emits:** ``pitch.drafted`` (one per company; tagged ``requires_human``).
- **Kind:** agentic.

Why per-company events and not a single batch event? Because each company is a
**separate review item**: the founder approves, edits, or rejects them
independently in the existing review surface. The ``human-review-queue`` already
parks per-event, so we get per-pitch approval for free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from flywheel.core.agent import Agent, SingleCallAgent
from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.llm_gateway import FakeLLMGateway, LLMGateway


class Pitch(BaseModel):
    """The structured per-company pitch the agent produces.

    Carries both an **email** form (subject + body, when we have an address) and
    a **LinkedIn** form (DM/InMail body), so the founder can choose the channel
    at review time. The two share the same opening angle by construction.
    """

    company: str = ""
    contact_email: str = ""
    angle: str = ""  # The one-line opener the rest of the pitch leans on.
    email_subject: str = ""
    email_body: str = ""
    linkedin_message: str = ""


def _build_prompt(inputs: Mapping[str, Any]) -> str:
    """Render one company's inferred need into a prompt for the agent."""
    company = inputs.get("company", "")
    top_need = inputs.get("top_need", "")
    pitch_angle = inputs.get("pitch_angle", "")
    buying_signals = inputs.get("buying_signals", []) or []
    offer = inputs.get("offer", "")
    contact_email = inputs.get("contact_email", "")

    lines = [
        "Draft a tailored outbound pitch for this company.",
        f"Company: {company}",
        f"Their top need: {top_need}" if top_need else "",
        f"Buying signals: {', '.join(buying_signals)}" if buying_signals else "",
        f"Suggested angle: {pitch_angle}" if pitch_angle else "",
        f"Our offer: {offer}" if offer else "",
        f"Contact email (use as-is): {contact_email}" if contact_email else "",
        "",
        "Produce both an EMAIL (subject + short, specific body) and a LinkedIn",
        "DM variant (shorter, less formal). Open with the angle. End with a",
        "clear, low-friction ask.",
        "Return a structured Pitch.",
    ]
    return "\n".join(line for line in lines if line)


class PitchGenerator:
    name = "pitch-generator"
    version = "0.1.0"
    kind = "agentic"
    reacts_to = ["company.needs.profiled"]
    emits = ["pitch.drafted"]
    calls = ["llm-gateway"]

    def __init__(
        self,
        *,
        gateway: LLMGateway | None = None,
        agent: Agent | None = None,
    ) -> None:
        self._agent = agent or SingleCallAgent(
            gateway or FakeLLMGateway(), _build_prompt
        )

    def handle(self, event: Event, ctx: NodeContext) -> None:
        offer = event.payload.get("offer", "")
        for company in event.payload.get("companies", []):
            pitch, _completion = self._agent.run(
                {
                    "company": company.get("company", ""),
                    "top_need": company.get("top_need", ""),
                    "pitch_angle": company.get("pitch_angle", ""),
                    "buying_signals": company.get("buying_signals", []) or [],
                    "contact_email": company.get("contact_email", ""),
                    "offer": offer,
                },
                Pitch,
            )

            # Carry through fields the agent might omit, so downstream review
            # always has the company + email even with a sparse fake gateway.
            payload: dict[str, Any] = pitch.model_dump()
            payload.setdefault("company", company.get("company", ""))
            if not payload.get("contact_email"):
                payload["contact_email"] = company.get("contact_email", "")

            # Tag for the human-review-queue: every drafted pitch goes through
            # founder approval before any send (Wizard-of-Oz outreach).
            ctx.emit(
                type="pitch.drafted",
                payload=payload,
                tags={"requires_human": True},
            )


# Re-export the module-level prompt builder so tests / agents can swap it.
build_prompt = _build_prompt


# Keep the schema importable at module top level for canned-gateway wiring,
# mirroring how ``MarketScanner`` exports ``MarketMap``.
__all__ = ["Pitch", "PitchGenerator", "build_prompt"]
