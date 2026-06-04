"""Core LLM service interface — available to ALL modules.

Modules call this interface for LLM access. The implementation lives in
modules/agent_runtime/llm_gateway.py but modules never import it directly.
"""

from __future__ import annotations

from typing import Any

from ai_flywheel.core.contracts.schemas import LLMResponse

# Late-bound reference to the gateway implementation
_gateway = None


def _get_gateway():
    """Lazy import to avoid circular dependencies."""
    global _gateway
    if _gateway is None:
        from ai_flywheel.modules.agent_runtime.llm_gateway import LLMGateway

        _gateway = LLMGateway()
    return _gateway


async def generate(
    messages: list[dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    idempotency_key: str | None = None,
    fallback_models: list[str] | None = None,
    venture_id: str | None = None,
    module_name: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> LLMResponse:
    """Generate a completion via the LLM Gateway.

    Any module can call this. Cost tracking and tracing happen automatically.

    Args:
        messages: Chat messages in OpenAI format
        model: Primary model (litellm model string)
        temperature: Sampling temperature
        max_tokens: Max response tokens
        idempotency_key: Temporal Activity ID for retry safety
        fallback_models: Models to try if primary fails
        venture_id: For cost attribution
        module_name: For trace attribution
        metadata: Additional context

    Returns:
        LLMResponse with content, cost, and token counts
    """
    gateway = _get_gateway()
    return await gateway.complete(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        idempotency_key=idempotency_key,
        fallback_models=fallback_models,
        venture_id=venture_id,
        module_name=module_name,
        metadata=metadata,
    )
