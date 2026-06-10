"""``insight-inferrer`` — the founder-facing payoff of the ingestion flywheel.

> *The knowledge graph + materialized views are the substrate. The value is the
> decoupled inference that runs over them: "Company Y posted a content role ⇒ Y
> likely needs ghostwriting"; "a spike of negative reviews about feature X at
> company Y ⇒ churn/displacement risk." Each becomes a founder notification.*

An **agentic** node (LLM-driven, behind the same ``Agent`` / ``SingleCallAgent``
seam every agentic node uses) that:

  1. **Reacts to** ``knowledge.updated`` / ``tick.daily``.
  2. **Reads** the knowledge graph + views (companies, open roles, sentiment).
  3. **Reasons** over that context with the LLM to surface decoupled market
     insights (lead opportunities + risk signals), each with a recommended
     action and an urgency.
  4. **Emits** one ``market.insight`` per insight (for the UI / Layer 3) AND a
     ``signal.verdict`` per high-value insight so the existing
     ``founder-notifier`` routes it to Slack/email — **no new notification
     machinery** (registry-time wiring reuse).

- **Reacts to:** ``knowledge.updated``, ``tick.daily``.
- **Calls:** ``knowledge-store``, ``inferencer`` (llm-gateway).
- **Emits:** ``market.insight``, ``signal.verdict``.
- **Kind:** agentic.

Fake-by-default: a ``FakeLLMGateway`` (with a canned builder) makes the whole
path deterministic offline; ``config: {live: true}`` swaps in ``LiteLLMGateway``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from flywheel.core.agent import Agent, SingleCallAgent
from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.llm_gateway import FakeLLMGateway, LLMGateway
from flywheel.persistence.knowledge_store import InMemoryKnowledgeStore, KnowledgeStore

# Verdicts the founder-notifier treats as urgent (Slack + email).
_URGENT = "strong"


class Insight(BaseModel):
    """One decoupled, founder-facing market insight."""

    kind: str = ""  # "lead_opportunity" | "risk_signal" | ...
    company: str = ""
    headline: str = ""
    rationale: str = ""
    recommended_action: str = ""
    # Inference confidence in [0, 1]; high-confidence leads/risks notify urgently.
    confidence: float = 0.0
    urgent: bool = False


class InsightSet(BaseModel):
    """The structured output of one inference pass."""

    insights: list[Insight] = Field(default_factory=list)


def _build_insight_prompt(inputs: Mapping[str, Any]) -> str:
    """Render the current graph/view context into a single reasoning prompt."""
    return (
        "You are a market-exploration analyst for a founder. You are given a "
        "snapshot of a knowledge graph built from public data sources (job "
        "postings, product reviews). Infer DECOUPLED, actionable market "
        "insights: e.g. a company hiring for a content/brand role likely needs "
        "ghostwriting; a spike of negative reviews about a product signals "
        "churn/displacement risk and an outreach opening.\n\n"
        "For each insight give: kind (lead_opportunity|risk_signal), company, a "
        "one-line headline, a short rationale citing the signal, a recommended "
        "action, a confidence in [0,1], and whether it is urgent.\n\n"
        f"Open roles by company:\n{inputs.get('open_roles', '')}\n\n"
        f"Sentiment by company:\n{inputs.get('sentiment', '')}\n"
    )


class InsightInferrer:
    name = "insight-inferrer"
    version = "0.1.0"
    kind = "agentic"
    reacts_to = ["knowledge.updated", "tick.daily"]
    emits = ["market.insight", "signal.verdict"]
    calls = ["knowledge-store", "inferencer"]

    def __init__(
        self,
        *,
        knowledge_store: KnowledgeStore | None = None,
        gateway: LLMGateway | None = None,
        agent: Agent | None = None,
        min_confidence: float = 0.5,
    ) -> None:
        self._knowledge = knowledge_store or InMemoryKnowledgeStore()
        gw = gateway or FakeLLMGateway()
        self._agent = agent or SingleCallAgent(gw, _build_insight_prompt)
        self._min_confidence = min_confidence

    def handle(self, event: Event, ctx: NodeContext) -> None:
        vid = event.venture_id
        context = self._gather_context(vid)
        # Nothing in the graph yet → nothing to infer.
        if not context["open_roles"] and not context["sentiment"]:
            return

        result, _completion = self._agent.run(context, InsightSet)
        for insight in result.insights:
            if insight.confidence < self._min_confidence:
                continue
            # Surface to the UI / Layer 3.
            ctx.emit(
                type="market.insight",
                payload=insight.model_dump(),
            )
            # Route high-value insights to the founder via the existing notifier,
            # which reacts to signal.verdict (urgent => Slack + email).
            ctx.emit(
                type="signal.verdict",
                payload={
                    "verdict": _URGENT if insight.urgent else "weak",
                    "confidence": insight.confidence,
                    "explanation": f"{insight.headline} — {insight.recommended_action}",
                    "company": insight.company,
                    "insight_kind": insight.kind,
                },
                tags={"urgent": True} if insight.urgent else {},
            )

    def _gather_context(self, venture_id: str) -> dict[str, Any]:
        roles_view = self._knowledge.get_view("open_roles_by_company", venture_id)
        sentiment_view = self._knowledge.get_view("recent_sentiment_by_company", venture_id)
        return {
            "open_roles": roles_view.rows if roles_view else [],
            "sentiment": sentiment_view.rows if sentiment_view else [],
        }
