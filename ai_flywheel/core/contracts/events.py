"""Typed event contracts for inter-module communication.

Both publisher and subscriber import from here — ensuring type safety
without coupling modules to each other.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AgentCompletedEvent(BaseModel):
    """Fired when an agent finishes executing a task."""

    agent_id: str
    venture_id: str
    task_id: str
    duration_ms: float
    cost_usd: float
    tokens_input: int
    tokens_output: int
    output_quality: float | None = None
    model_used: str
    timestamp: datetime


class WorkflowCompletedEvent(BaseModel):
    """Fired when a Temporal workflow completes."""

    workflow_id: str
    venture_id: str
    workflow_type: str
    duration_ms: float
    total_cost_usd: float
    step_count: int
    status: str  # "completed", "failed", "cancelled"
    timestamp: datetime


class LLMCallCompletedEvent(BaseModel):
    """Fired after every LLM call for cost tracking."""

    venture_id: str | None
    module_name: str
    model: str
    provider: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: float
    cached: bool
    timestamp: datetime


class CostThresholdBreachedEvent(BaseModel):
    """Fired when a venture's cost exceeds its configured threshold."""

    venture_id: str
    current_spend_usd: float
    threshold_usd: float
    period: str
    top_contributor_module: str
    timestamp: datetime


class VentureCreatedEvent(BaseModel):
    """Fired when a new venture is created."""

    venture_id: str
    name: str
    domain: str
    timestamp: datetime
