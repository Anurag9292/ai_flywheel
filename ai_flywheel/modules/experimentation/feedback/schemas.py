"""Pydantic schemas for Feedback Collector.

Defines the API contract for collecting, querying, and summarizing feedback.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Schema for collecting a new feedback item."""

    feedback_type: str = Field(..., pattern=r"^(explicit|implicit|automated)$")
    category: str = Field(
        ...,
        pattern=r"^(rating|correction|preference|click|ignore|retry|escalation|metric)$",
    )
    source_module: str
    target_module: str | None = None
    entity_id: str
    entity_type: str = Field(
        ..., pattern=r"^(agent_output|prompt|tool|recommendation)$"
    )
    rating: float | None = None
    correction_text: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None


class FeedbackResponse(BaseModel):
    """Schema for feedback item responses."""

    id: str
    venture_id: str
    feedback_type: str
    category: str
    source_module: str
    target_module: str | None
    entity_id: str
    entity_type: str
    rating: float | None
    correction_text: str | None
    context: dict[str, Any]
    quality_score: float
    user_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackSummary(BaseModel):
    """Aggregated feedback summary for an entity."""

    entity_id: str
    entity_type: str
    total_feedback: int
    avg_rating: float | None
    positive_count: int
    negative_count: int
    correction_count: int
    recent_feedback: list[FeedbackResponse]


class FeedbackQuery(BaseModel):
    """Query parameters for filtering feedback."""

    entity_id: str | None = None
    entity_type: str | None = None
    feedback_type: str | None = None
    category: str | None = None
    source_module: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
