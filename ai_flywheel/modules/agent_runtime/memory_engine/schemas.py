"""Pydantic schemas for the Memory Engine module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryStore(BaseModel):
    """Request schema for storing a new memory."""

    agent_id: str | None = None
    tier: str
    content: str
    importance: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryQuery(BaseModel):
    """Request schema for querying memories."""

    agent_id: str | None = None
    tier: str | None = None
    query: str | None = None
    limit: int = 10
    min_importance: float = 0.0


class MemoryResponse(BaseModel):
    """Response schema for a single memory entry."""

    id: str
    venture_id: str
    agent_id: str | None
    memory_tier: str
    content: str
    summary: str | None
    importance: float
    access_count: int
    metadata: dict[str, Any] | None
    created_at: datetime
    last_accessed_at: datetime | None

    model_config = {"from_attributes": True}


class MemoryContext(BaseModel):
    """Aggregated context window built from all memory tiers."""

    working: list[MemoryResponse] = Field(default_factory=list)
    episodic: list[MemoryResponse] = Field(default_factory=list)
    semantic: list[MemoryResponse] = Field(default_factory=list)
    procedural: list[MemoryResponse] = Field(default_factory=list)
    total_tokens_estimate: int = 0


class ConsolidateRequest(BaseModel):
    """Request schema for memory consolidation."""

    venture_id: str
    agent_id: str | None = None
    max_age_hours: int = 168
