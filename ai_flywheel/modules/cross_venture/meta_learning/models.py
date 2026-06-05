"""SQLAlchemy models for Meta-Learning & Flywheel Engine.

FlywheelMetric: Per-venture periodic metrics for velocity calculation.
CrossVentureInsight: AI-generated insights across ventures.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel


class FlywheelMetric(BaseModel):
    """A periodic metric for a venture used to calculate flywheel velocity."""

    __tablename__ = "flywheel_metrics"

    venture_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    period: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "2026-W22", "2026-06"
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CrossVentureInsight(BaseModel):
    """An insight generated from cross-venture analysis."""

    __tablename__ = "cross_venture_insights"

    insight_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "pattern_discovered"|"acceleration_detected"|"bottleneck_identified"|"recommendation"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    affected_ventures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
