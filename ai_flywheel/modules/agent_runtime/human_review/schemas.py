"""Pydantic schemas for the Human Review Engine module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    """Request to submit an item for human review."""

    item_type: str
    content: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    source_agent_id: str | None = None
    source_workflow_id: str | None = None
    priority: str = "medium"
    confidence_score: float | None = None
    expires_in_hours: int | None = None


class ReviewResponse(BaseModel):
    """Response representing a review item."""

    id: str
    venture_id: str
    item_type: str
    status: str
    priority: str
    content: dict[str, Any]
    context: dict[str, Any]
    source_agent_id: str | None
    assigned_to: str | None
    decision: str | None
    reviewer_notes: str | None
    edited_content: dict[str, Any] | None
    confidence_score: float | None
    created_at: datetime
    reviewed_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class ReviewDecision(BaseModel):
    """Request to record a decision on a review item."""

    review_id: str
    decision: str
    notes: str = ""
    edited_content: dict[str, Any] | None = None


class ReviewPolicyCreate(BaseModel):
    """Request to create a review policy."""

    name: str
    trigger_condition: dict[str, Any]
    routing: dict[str, Any] = Field(default_factory=dict)


class ReviewPolicyResponse(BaseModel):
    """Response representing a review policy."""

    id: str
    venture_id: str
    name: str
    trigger_condition: dict[str, Any]
    routing: dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewQueue(BaseModel):
    """Aggregated view of the review queue."""

    items: list[ReviewResponse]
    total: int
    pending: int
    overdue: int
