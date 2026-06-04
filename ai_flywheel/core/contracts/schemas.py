"""Shared data transfer schemas used across module boundaries.

These are the typed contracts for synchronous inter-module communication
(the Data Gateway pattern from module-isolation.md).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LLMRequest(BaseModel):
    """Request to the LLM Gateway."""

    messages: list[dict[str, str]]
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int | None = None
    idempotency_key: str | None = None
    venture_id: str | None = None
    module_name: str = "unknown"


class LLMResponse(BaseModel):
    """Response from the LLM Gateway."""

    content: str
    model: str
    provider: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    cached: bool = False
    latency_ms: float = 0.0


class VentureInfo(BaseModel):
    """Public venture information available to all modules."""

    id: str
    name: str
    domain: str
    status: str
    config: dict


class CostSummary(BaseModel):
    """Cost summary for a venture over a time period."""

    venture_id: str
    period: str
    total_usd: float
    by_module: dict[str, float]
    by_provider: dict[str, float]
    by_model: dict[str, float]


class HealthStatus(BaseModel):
    """System health status."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    environment: str
    database: str
    redis: str
    temporal: str
    timestamp: datetime
