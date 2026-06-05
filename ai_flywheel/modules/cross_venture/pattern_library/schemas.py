"""Pydantic schemas for Pattern & Template Library."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PatternCreate(BaseModel):
    """Request to create a new pattern."""

    name: str
    description: str
    pattern_type: str
    content: dict
    tags: list[str] = []
    source_venture_id: str | None = None


class PatternResponse(BaseModel):
    """Pattern data returned to clients."""

    id: str
    name: str
    description: str
    pattern_type: str
    content: dict
    tags: list[str]
    source_venture_id: str | None
    success_count: int
    failure_count: int
    confidence_score: float
    version: int
    is_active: bool
    created_at: datetime


class PatternSearchRequest(BaseModel):
    """Request to search patterns."""

    query: str | None = None
    pattern_type: str | None = None
    tags: list[str] | None = None
    min_confidence: float = 0.0
    limit: int = 20


class PatternSearchResult(BaseModel):
    """Search results."""

    patterns: list[PatternResponse]
    total: int


class ApplyPatternRequest(BaseModel):
    """Request to apply a pattern to a venture."""

    pattern_id: str
    venture_id: str
    outcome: str = "success"
    notes: str = ""


class ApplyPatternResult(BaseModel):
    """Result of applying a pattern."""

    pattern_id: str
    new_confidence: float
    total_applications: int
