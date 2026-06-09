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

import json
import os
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

import structlog
from pydantic import BaseModel

log = structlog.get_logger("flywheel.llm_gateway")

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


# Default model for live reasoning; override with FLYWHEEL_LLM_MODEL.
DEFAULT_LLM_MODEL = "gpt-4o-mini"


class LiteLLMGateway:
    """Real, multi-provider gateway backed by ``litellm`` (the ``lead-gen`` extra).

    Structured-output first, same contract as :class:`FakeLLMGateway`: it asks
    the model to return JSON matching ``schema`` (via ``response_format`` JSON
    schema), parses it into the Pydantic type, and reports a real
    :class:`Completion` (model, token counts, cost) so the trace-recorder shows
    actual cost/latency instead of zeros.

    Model is ``FLYWHEEL_LLM_MODEL`` (default ``gpt-4o-mini``); the provider key
    (e.g. ``OPENAI_API_KEY``) is read by litellm from the environment. ``litellm``
    is imported lazily so nothing requires it unless a venture wires this in;
    a missing extra surfaces as a clear ``RuntimeError``.
    """

    def __init__(self, model: str | None = None, *, temperature: float = 0.3) -> None:
        self.model = model or os.environ.get("FLYWHEEL_LLM_MODEL", DEFAULT_LLM_MODEL)
        self._temperature = temperature

    def complete(self, prompt: str, schema: type[T]) -> tuple[T, Completion]:
        try:
            import litellm  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "Live reasoning needs the 'lead-gen' extra (litellm). Install it: "
                "uv pip install -e '.[lead-gen]'."
            ) from exc

        # Ask for JSON matching the schema. litellm normalizes response_format
        # across providers; for OpenAI-class models this uses structured output.
        response = litellm.completion(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You return only a JSON object matching the requested "
                        "schema. No prose, no markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self._temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                },
            },
        )

        content = response.choices[0].message.content or "{}"
        try:
            parsed = schema.model_validate(json.loads(content))
        except Exception:
            log.warning("llm_gateway.parse_failed", model=self.model, content=content[:200])
            raise

        usage = getattr(response, "usage", None)
        completion = Completion(
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cost_usd=_response_cost(response),
        )
        return parsed, completion


def _response_cost(response: Any) -> float:
    """Best-effort USD cost from a litellm response (0.0 if unavailable).

    Two sources, in order:
    1. ``response._hidden_params["response_cost"]`` — litellm pre-computes this
       for many providers.
    2. ``litellm.completion_cost(response)`` — computes from model + token usage
       when (1) is absent (common: it was returning 0.0 in real runs).
    """
    hidden = getattr(response, "_hidden_params", None) or {}
    cost = hidden.get("response_cost") if isinstance(hidden, dict) else None
    try:
        if cost is not None:
            value = float(cost)
            if value > 0.0:
                return value
    except (TypeError, ValueError):
        pass

    # Fallback: ask litellm to compute it from the response's usage + model.
    try:
        import litellm

        computed = litellm.completion_cost(completion_response=response)
        return float(computed) if computed else 0.0
    except Exception:  # noqa: BLE001 — cost is best-effort observability, never fatal
        return 0.0
