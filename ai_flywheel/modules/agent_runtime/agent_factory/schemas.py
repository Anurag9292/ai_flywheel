"""Pydantic schemas for Agent Factory — request/response validation.

These schemas define the API contract for creating, updating, and executing agents.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentBlueprintCreate(BaseModel):
    """Schema for creating a new agent blueprint."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    agent_type: str = Field(default="single", pattern=r"^(single|chain|parallel|router)$")
    model: str = Field(default="gpt-4o-mini", max_length=100)
    system_prompt: str | None = None
    tools: list[str] = Field(default_factory=list)
    memory_tiers: dict[str, Any] = Field(default_factory=dict)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout_seconds: int = Field(default=120, ge=1, le=3600)
    retry_policy: dict[str, Any] = Field(
        default_factory=lambda: {"maximum_attempts": 3, "backoff_coefficient": 2.0}
    )


class AgentBlueprintUpdate(BaseModel):
    """Schema for updating an agent blueprint. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    agent_type: str | None = Field(default=None, pattern=r"^(single|chain|parallel|router)$")
    model: str | None = Field(default=None, max_length=100)
    system_prompt: str | None = None
    tools: list[str] | None = None
    memory_tiers: dict[str, Any] | None = None
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)
    retry_policy: dict[str, Any] | None = None
    is_active: bool | None = None


class AgentBlueprintResponse(BaseModel):
    """Schema for agent blueprint responses."""

    id: str
    venture_id: str
    name: str
    description: str | None
    agent_type: str
    model: str
    system_prompt: str | None
    tools: list[str] | None
    memory_tiers: dict[str, Any] | None
    max_tokens: int
    temperature: float
    timeout_seconds: int
    retry_policy: dict[str, Any] | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentExecutionRequest(BaseModel):
    """Request to execute an agent. Specify either agent_id or agent_name."""

    agent_id: str | None = None
    agent_name: str | None = None
    task: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    require_approval: bool = False


class AgentExecutionResult(BaseModel):
    """Result of an agent execution."""

    execution_id: str
    agent_id: str
    status: str  # "completed", "failed", "pending_approval", "rejected"
    output: str | None = None
    cost_usd: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: float = 0.0
    trace_id: str | None = None
