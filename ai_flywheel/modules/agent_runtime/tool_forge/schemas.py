"""Pydantic schemas for Tool Forge — request/response validation.

These schemas define the API contract for registering, invoking, and searching tools.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCreate(BaseModel):
    """Schema for registering a new tool."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(
        default="custom",
        pattern=r"^(api|data|communication|payment|deployment|analytics|custom)$",
    )
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class ToolUpdate(BaseModel):
    """Schema for updating a tool definition. All fields optional."""

    description: str | None = None
    category: str | None = Field(
        default=None,
        pattern=r"^(api|data|communication|payment|deployment|analytics|custom)$",
    )
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class ToolResponse(BaseModel):
    """Schema for tool definition responses."""

    id: str
    venture_id: str
    name: str
    description: str | None
    category: str
    input_schema: dict[str, Any] | None
    output_schema: dict[str, Any] | None
    config: dict[str, Any] | None
    version: int
    is_active: bool
    reliability_score: float
    avg_latency_ms: float
    total_invocations: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolInvokeRequest(BaseModel):
    """Request to invoke a tool. Specify either tool_id or tool_name."""

    tool_id: str | None = None
    tool_name: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    agent_id: str | None = None
    timeout_ms: int = Field(default=30000, ge=100, le=300000)


class ToolInvokeResult(BaseModel):
    """Result of a tool invocation."""

    execution_id: str
    tool_id: str
    status: str  # success|failure|timeout
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float
    cost_usd: float = 0.0


class ToolSearchRequest(BaseModel):
    """Request to search for tools by keyword."""

    query: str = Field(..., min_length=1)
    category: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class ToolSearchResult(BaseModel):
    """Result of a tool search."""

    tools: list[ToolResponse]
    query: str
