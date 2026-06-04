"""LLM Gateway — unified LLM access with cost tracking and idempotency.

Every LLM call goes through this gateway. Provides:
- Multi-provider access via litellm
- Cost tracking per call (attributed to venture/module)
- Idempotent caching by activity_id (Temporal retry safety)
- Fallback chains (primary → fallback on failure)
- Tracing integration (every call = a span)
"""

from __future__ import annotations

import time
from typing import Any

import litellm
import structlog

from ai_flywheel.core.config import settings
from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.core.traces import get_tracer

logger = structlog.get_logger()

# Configure litellm
litellm.drop_params = True
litellm.success_callback = []
litellm.failure_callback = []


class LLMGateway:
    """Unified LLM access with cost tracking and idempotency."""

    def __init__(self) -> None:
        self._cache: dict[str, LLMResponse] = {}
        self._tracer = get_tracer()

        if settings.openai_api_key:
            litellm.api_key = settings.openai_api_key
        if settings.anthropic_api_key:
            litellm.anthropic_key = settings.anthropic_api_key

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        idempotency_key: str | None = None,
        fallback_models: list[str] | None = None,
        venture_id: str | None = None,
        module_name: str = "llm_gateway",
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Complete a chat message with an LLM."""
        # Check idempotency cache
        if idempotency_key and idempotency_key in self._cache:
            cached = self._cache[idempotency_key]
            logger.info("llm_cache_hit", key=idempotency_key, model=cached.model)
            return LLMResponse(
                content=cached.content,
                model=cached.model,
                provider=cached.provider,
                tokens_input=cached.tokens_input,
                tokens_output=cached.tokens_output,
                cost_usd=cached.cost_usd,
                cached=True,
                latency_ms=0.0,
            )

        # Try primary + fallbacks
        models_to_try = [model] + (fallback_models or [])
        last_error: Exception | None = None

        for attempt_model in models_to_try:
            try:
                response = await self._call_model(
                    messages=messages,
                    model=attempt_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    venture_id=venture_id,
                    module_name=module_name,
                )

                if idempotency_key:
                    self._cache[idempotency_key] = response

                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    "llm_model_failed",
                    model=attempt_model,
                    error=str(e),
                    remaining=len(models_to_try) - models_to_try.index(attempt_model) - 1,
                )

        raise LLMError(
            f"All models failed. Last error: {last_error}",
            models_tried=models_to_try,
        )

    async def _call_model(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
        venture_id: str | None,
        module_name: str,
    ) -> LLMResponse:
        """Make the actual LLM API call with tracing."""
        async with self._tracer.span(
            module_name=module_name,
            operation="llm_complete",
            input_data={"model": model, "message_count": len(messages)},
        ) as span:
            start = time.perf_counter()

            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response = await litellm.acompletion(**kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            content = response.choices[0].message.content or ""
            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0

            # Calculate cost
            try:
                cost = litellm.completion_cost(
                    model=model,
                    prompt=str(tokens_in),
                    completion=str(tokens_out),
                )
            except Exception:
                cost = 0.0

            provider = self._get_provider(model)

            span.set_cost(
                cost_usd=cost,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                model=model,
            )
            span.output_data = {
                "content_length": len(content),
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "cost_usd": cost,
            }

            logger.info(
                "llm_complete",
                model=model,
                provider=provider,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=f"${cost:.6f}",
                latency_ms=f"{elapsed_ms:.0f}",
                venture_id=venture_id,
            )

            return LLMResponse(
                content=content,
                model=model,
                provider=provider,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                cost_usd=cost,
                cached=False,
                latency_ms=elapsed_ms,
            )

    def _get_provider(self, model: str) -> str:
        """Determine provider from model string."""
        if "claude" in model or "anthropic" in model:
            return "anthropic"
        if "gpt" in model or "o1" in model:
            return "openai"
        if "gemini" in model:
            return "google"
        return "unknown"

    def get_cache_stats(self) -> dict[str, Any]:
        return {
            "cached_responses": len(self._cache),
            "total_cost_cached": sum(r.cost_usd for r in self._cache.values()),
        }

    def clear_cache(self) -> None:
        self._cache.clear()


class LLMError(Exception):
    """Raised when all LLM models fail."""

    def __init__(self, message: str, models_tried: list[str] | None = None):
        super().__init__(message)
        self.models_tried = models_tried or []
