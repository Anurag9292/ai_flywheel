"""``llm-gateway`` — derived in PostlineAI Step 2.

A **library tool** (leaf I/O): the multi-provider model gateway every agentic
node calls. It is *not* event-driven — you import it and call ``complete()``.

Per ``new_docs/stack.md`` we ship the **fake** now (deterministic, offline) and
defer the real ``litellm``-backed impl until a step needs live calls. Both sit
behind the ``LLMGateway`` Protocol, so swapping is a one-line change at the
call site and nothing else in the system knows.

The gateway is intentionally *structured-output first*: ``complete()`` takes a
Pydantic schema and returns an instance of it. That keeps every agentic node's
"one structured LLM call" shape (the ``SingleCallAgent`` in ``core/agent.py``)
honest and typed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# A canned builder turns a prompt into a dict of field values for a schema.
CannedBuilder = Callable[[str], dict[str, Any]]


class Completion(BaseModel):
    """What a gateway call reports back alongside the parsed output, so the
    trace-recorder can attribute cost/latency once real providers are wired.
    """

    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


@runtime_checkable
class LLMGateway(Protocol):
    """The model-gateway contract. Structured-output first."""

    def complete(self, prompt: str, schema: type[T]) -> tuple[T, Completion]:
        """Run one completion and parse it into ``schema``.

        Returns the parsed model plus a ``Completion`` describing the call
        (model name, token counts, cost) for observability.
        """
        ...


class FakeLLMGateway:
    """Deterministic, offline gateway for development and tests.

    It does not call any provider. Instead it constructs a *plausible* instance
    of the requested schema from a registry of canned builders keyed by schema
    name, falling back to schema defaults. This lets agentic nodes run
    end-to-end with zero network and fully reproducible output.
    """

    def __init__(self, model: str = "fake/echo-1") -> None:
        self.model = model
        # schema __name__ -> builder(prompt) -> dict of field values
        self._canned: dict[str, CannedBuilder] = {}

    def register(self, schema_name: str, builder: CannedBuilder) -> None:
        """Register a canned builder for a given schema name (test hook)."""
        self._canned[schema_name] = builder

    def complete(self, prompt: str, schema: type[T]) -> tuple[T, Completion]:
        builder = self._canned.get(schema.__name__)
        if builder is not None:
            data = builder(prompt)
            parsed = schema.model_validate(data)
        else:
            # No canned builder: construct from schema defaults where possible.
            parsed = schema()
        completion = Completion(
            model=self.model,
            prompt_tokens=len(prompt.split()),
            completion_tokens=0,
            cost_usd=0.0,
        )
        return parsed, completion
