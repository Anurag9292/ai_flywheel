"""``company-needs-analyzer`` — derived in PostlineAI's outbound lead-gen step.

> *The venture needs to: read what each discovered company is hiring for and
> infer **what they most need right now** — the angle a tailored pitch should
> open with.*

An **event-driven node** (agentic) that reacts to ``companies.discovered``,
hands the batch of company leads to its ``Agent`` for one structured LLM call,
and emits ``company.needs.profiled`` carrying the structured analysis.

- **Reacts to:** ``companies.discovered``.
- **Calls:** ``llm-gateway`` (via its ``Agent``).
- **Emits:** ``company.needs.profiled``.
- **Kind:** agentic.

Like the other agentic nodes (``market-scanner``, ``pain-extractor``), the
``Agent`` is constructor-injected and defaults to a :class:`SingleCallAgent`
over a :class:`FakeLLMGateway`, so the node runs deterministically in tests
and the dev runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from flywheel.core.agent import Agent, SingleCallAgent
from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.llm_gateway import FakeLLMGateway, LLMGateway


class CompanyNeed(BaseModel):
    """One company's inferred top need + the buying signals that support it."""

    company: str = ""
    top_need: str = ""
    buying_signals: list[str] = Field(default_factory=list)
    # 0.0 (poor fit for the venture's offer) .. 1.0 (perfect fit).
    fit_score: float = 0.0
    # Free-form: a one-line angle the pitch-generator can lean on.
    pitch_angle: str = ""
    # Carried through from upstream so the pitch-generator can address an email
    # without re-deriving it. Empty when the lead-sourcer didn't find one.
    contact_email: str = ""


class CompanyNeedsReport(BaseModel):
    """The structured output the agent produces and the node emits."""

    companies: list[CompanyNeed] = Field(default_factory=list)


def _build_prompt(inputs: Mapping[str, Any]) -> str:
    """Render discovered companies + their postings into one prompt."""
    icp = inputs.get("icp", "")
    offer = inputs.get("offer", "")
    leads = inputs.get("companies", [])
    lines: list[str] = [
        "Analyze the following companies and infer what each most needs right now,",
        "based on the roles they are hiring for and any career-page signal.",
        f"Our ICP: {icp}" if icp else "",
        f"Our offer: {offer}" if offer else "",
        "",
        "Companies:",
    ]
    for lead in leads:
        lines.append(f"- Company: {lead.get('company', '')}")
        lines.append(f"  Contact email: {lead.get('contact_email', '') or '(unknown)'}")
        for posting in lead.get("postings", []):
            title = posting.get("title", "")
            location = posting.get("location", "")
            desc = (posting.get("description", "") or "").strip()
            lines.append(f"  - Posting: {title} ({location})")
            if desc:
                lines.append(f"    Snippet: {desc}")
        snippet = (lead.get("career_page_snippet", "") or "").strip()
        if snippet:
            lines.append(f"  Career page: {snippet}")
    lines.append("")
    lines.append(
        "For each company return: top_need, buying_signals, fit_score (0..1), "
        "pitch_angle. Keep contact_email as given."
    )
    lines.append("Return a structured CompanyNeedsReport.")
    return "\n".join(line for line in lines if line)


class CompanyNeedsAnalyzer:
    name = "company-needs-analyzer"
    version = "0.1.0"
    kind = "agentic"
    reacts_to = ["companies.discovered"]
    emits = ["company.needs.profiled"]
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
        leads: list[dict[str, Any]] = list(event.payload.get("companies", []))
        # ICP / offer travel in the event payload (rubric-style), so the node
        # itself stays venture-agnostic. The dev runtime seeds them from the
        # venture's domain block (see registry / topology).
        icp = event.payload.get("icp", "")
        offer = event.payload.get("offer", "")

        report, _completion = self._agent.run(
            {"icp": icp, "offer": offer, "companies": leads},
            CompanyNeedsReport,
        )

        # Best-effort: carry through contact_email from the upstream lead when
        # the agent didn't echo one back. This keeps fake-driven runs cheap
        # without making the prompt brittle.
        emails_by_company = {
            lead.get("company", ""): lead.get("contact_email", "") for lead in leads
        }
        for company in report.companies:
            if not company.contact_email:
                company.contact_email = emails_by_company.get(company.company, "")

        # Forward the offer so the (downstream) pitch-generator prompt keeps it.
        payload = report.model_dump()
        payload["offer"] = offer
        ctx.emit(
            type="company.needs.profiled",
            payload=payload,
        )
