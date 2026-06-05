"""SQLAlchemy models for the Human Review Engine module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class ReviewItem(BaseModel, VentureScopedMixin):
    """An item submitted for human review.

    Items flow through: pending → approved|rejected|edited|expired
    """

    __tablename__ = "review_items"

    item_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="agent_output|content|decision|tool_call",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending|approved|rejected|edited|expired",
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        index=True,
        comment="low|medium|high|critical",
    )

    content: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="The item to review",
    )

    context: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Why review is needed",
    )

    source_agent_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    source_workflow_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    assigned_to: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    decision: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="approve|reject|edit",
    )

    reviewer_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    edited_content: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Agent confidence that triggered review",
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ReviewPolicy(BaseModel, VentureScopedMixin):
    """A policy that governs when items are sent for human review."""

    __tablename__ = "review_policies"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    trigger_condition: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Conditions: {module, confidence_below, item_type, always}",
    )

    routing: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Routing: {assign_to, escalate_after_hours, auto_approve_above}",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
