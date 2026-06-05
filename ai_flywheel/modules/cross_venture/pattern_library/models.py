"""SQLAlchemy models for Pattern & Template Library.

Pattern: A reusable pattern (global, not venture-scoped) with confidence scoring.
PatternApplication: Records when a pattern is applied to a venture.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel


class Pattern(BaseModel):
    """A reusable pattern shared across ventures."""

    __tablename__ = "patterns"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    pattern_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # agent_config|prompt_template|workflow|tool_composition|evaluation_suite|feature_recipe
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    source_venture_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None
    )
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PatternApplication(BaseModel):
    """Records when a pattern is applied to a venture."""

    __tablename__ = "pattern_applications"

    venture_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pattern_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patterns.id"), nullable=False, index=True
    )
    outcome: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "success"|"failure"|"partial"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
