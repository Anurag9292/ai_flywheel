"""``signal-analyzer`` — derived in PostlineAI Step 4 (an *agentic* node).

> *The venture needs to: judge whether the conversion signal is strong, weak, or
> kill-worthy — given the working thesis ("would pay $499/mo").*

This is judgment, not API stitching — so it is the single **agentic** node that
decides "is this signal good?". It is reused across ad tests, product
engagement, and growth: the **rubric is passed in** (via the reacting event's
payload or, later, read from venture state), so the node itself stays generic.
That is the Step-6 reuse the walkthrough calls for, designed in from the start.

- **Reacts to:** ``campaign.metrics.updated`` (later also ``post.metrics.updated``,
  ``survey.responded`` — added by subscription, no code change).
- **Calls:** ``llm-gateway`` (via its ``Agent``).
- **Emits:** ``signal.verdict`` (``strong | weak | kill`` + confidence + why).
- **Kind:** agentic.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from flywheel.core.agent import Agent, SingleCallAgent
from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.llm_gateway import FakeLLMGateway, LLMGateway

DEFAULT_RUBRIC = (
    "Judge whether this venture has demand worth pursuing, given its thesis."
)


class SignalVerdict(BaseModel):
    """The structured output the agent produces and the node emits."""

    verdict: str = "weak"  # one of: strong | weak | kill
    confidence: float = 0.0  # 0.0 .. 1.0
    explanation: str = ""


def _build_prompt(inputs: Mapping[str, Any]) -> str:
    """Render the metrics + rubric into a single prompt for the agent."""
    rubric = inputs.get("rubric", DEFAULT_RUBRIC)
    metrics = inputs.get("metrics", {})
    lines = [
        "Decide if the signal below is strong, weak, or kill-worthy.",
        f"Success rubric for this stage: {rubric}",
        "Metrics:",
        *[f"  - {k}: {v}" for k, v in metrics.items()],
        "Return a structured SignalVerdict (verdict, confidence, explanation).",
    ]
    return "\n".join(lines)


class SignalAnalyzer:
    name = "signal-analyzer"
    version = "0.1.0"
    kind = "agentic"
    reacts_to = ["campaign.metrics.updated"]
    emits = ["signal.verdict"]
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
        # The rubric makes the node generic: each caller/venture supplies what
        # "good" means for the current stage. Falls back to a sane default.
        rubric = event.payload.get("rubric", DEFAULT_RUBRIC)
        # Everything except the rubric is treated as signal metrics.
        metrics = {k: v for k, v in event.payload.items() if k != "rubric"}

        verdict, _completion = self._agent.run(
            {"rubric": rubric, "metrics": metrics},
            SignalVerdict,
        )

        payload = verdict.model_dump()
        # Carry the source signal forward so the verdict is self-describing.
        payload["signal_from"] = event.type
        ctx.emit(type="signal.verdict", payload=payload)
