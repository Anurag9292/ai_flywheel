"""``pain-extractor`` — derived in PostlineAI Step 3 (an *agentic* node).

> *The venture needs to: ingest transcripts and extract pain points, frequency,
> and emotional intensity.*

An **event-driven node** that reacts to ``transcript.captured``, hands the
transcript text to its ``Agent`` (one structured LLM call), and emits
``pain.extracted`` carrying a structured ``PainReport``.

- **Reacts to:** ``transcript.captured``.
- **Calls:** ``llm-gateway`` (via its ``Agent``).
- **Emits:** ``pain.extracted``.
- **Kind:** agentic.

Like ``market-scanner``, the node **declares its own agent** (injected in
``__init__``, defaulting to a ``SingleCallAgent`` over a ``FakeLLMGateway``), so
``NodeContext`` / ``Runtime`` stay unchanged.

Reuse payoff: the existing ``thesis-tracker`` already subscribes to
``pain.extracted`` (via its ``EVIDENCE_MAP``, reading the ``pains`` field) and
maps it to the ``problem_is_real`` assumption — so this node feeds it with *zero*
wiring change. That is the event-driven payoff the walkthrough promises.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from flywheel.core.agent import Agent, SingleCallAgent
from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.llm_gateway import FakeLLMGateway, LLMGateway


class PainPoint(BaseModel):
    pain: str
    frequency: int = 1  # how many calls mentioned it
    intensity: float = 0.0  # 0.0 (mild) .. 1.0 (acute)


class PainReport(BaseModel):
    """The structured output the agent produces and the node emits."""

    pains: list[PainPoint] = Field(default_factory=list)


def _build_prompt(inputs: Mapping[str, Any]) -> str:
    """Render the transcript into a single prompt for the SingleCallAgent."""
    transcript = inputs.get("transcript", "")
    speaker = inputs.get("speaker", "")
    lines = [
        "Extract the customer pain points from this discovery-call transcript.",
        f"Speaker: {speaker}" if speaker else "",
        "Transcript:",
        f"  {transcript}",
        "For each pain, estimate its frequency and emotional intensity.",
        "Return a structured PainReport.",
    ]
    return "\n".join(line for line in lines if line)


class PainExtractor:
    name = "pain-extractor"
    version = "0.1.0"
    kind = "agentic"
    reacts_to = ["transcript.captured"]
    # Descriptive metadata for introspection / visualization.
    emits = ["pain.extracted"]
    calls = ["llm-gateway"]

    def __init__(
        self,
        *,
        gateway: LLMGateway | None = None,
        agent: Agent | None = None,
    ) -> None:
        # Node declares its own agent (default SingleCallAgent over fake gateway).
        self._agent = agent or SingleCallAgent(
            gateway or FakeLLMGateway(), _build_prompt
        )

    def handle(self, event: Event, ctx: NodeContext) -> None:
        transcript = event.payload.get("transcript", "")
        speaker = event.payload.get("speaker", "")

        # Hand the transcript to the agent for extraction (one structured call).
        report, _completion = self._agent.run(
            {"transcript": transcript, "speaker": speaker},
            PainReport,
        )

        # Emit the structured pains for anyone (thesis-tracker, Layer 3).
        ctx.emit(type="pain.extracted", payload=report.model_dump())
