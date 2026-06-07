"""The ``Agent`` seam — introduced in PostlineAI Step 2.

Per ``new_docs/stack.md`` ("Agent frameworks ... deferred behind an `Agent`
seam"): an agentic node does **not** talk to the LLM gateway directly, nor to a
framework like LangGraph. It talks to an ``Agent``:

    result = agent.run(inputs)   # structured in -> structured out

Today the only implementation we need is ``SingleCallAgent`` — one templated
``llm-gateway`` call producing a typed Pydantic output. That covers every
current agentic node (``market-scanner``, and later ``pain-extractor``,
``signal-analyzer``, ``voice-profile-builder``).

The point of the seam is that ``ToolLoopAgent`` (ReAct) and ``GraphAgent``
(where LangGraph / PydanticAI / a hand-rolled graph would plug in) can arrive
*later*, behind the identical ``run()`` interface — making the framework choice
a reversible, localized decision instead of a foundational bet.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from flywheel.libraries.llm_gateway import Completion, LLMGateway

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class Agent(Protocol):
    """Structured in → structured out. The node never knows which impl backs it."""

    def run(self, inputs: Mapping[str, Any], schema: type[T]) -> tuple[T, Completion]:
        ...


# A prompt template turns the node's inputs into the single prompt string.
PromptBuilder = Callable[[Mapping[str, Any]], str]


class SingleCallAgent:
    """One structured LLM call: inputs → prompt → ``gateway.complete`` → schema.

    This is the entire "agentic" surface we need for Step 2. It holds an
    ``LLMGateway`` (any impl behind the Protocol — ``FakeLLMGateway`` for now)
    and a ``PromptBuilder`` that renders the node's inputs into a prompt.
    """

    def __init__(self, gateway: LLMGateway, prompt_builder: PromptBuilder) -> None:
        self._gateway = gateway
        self._build_prompt = prompt_builder

    def run(self, inputs: Mapping[str, Any], schema: type[T]) -> tuple[T, Completion]:
        prompt = self._build_prompt(inputs)
        return self._gateway.complete(prompt, schema)
