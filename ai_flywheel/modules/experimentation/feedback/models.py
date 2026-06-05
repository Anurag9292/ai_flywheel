"""SQLAlchemy models for Feedback Collector.

FeedbackItem: A single piece of feedback (explicit, implicit, or automated)
collected about an entity (agent output, prompt, tool, recommendation).
"""

from __future__ import annotations

from sqlalchemy import Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class FeedbackItem(BaseModel, VentureScopedMixin):
    """A feedback signal collected about a platform entity."""

    __tablename__ = "feedback_items"

    feedback_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "explicit" | "implicit" | "automated"
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # "rating"|"correction"|"preference"|"click"|"ignore"|"retry"|"escalation"|"metric"
    source_module: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    target_module: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None
    )
    entity_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # What was being evaluated
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "agent_output" | "prompt" | "tool" | "recommendation"
    rating: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None
    )  # 1-5 or thumbs 0/1
    correction_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    quality_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
