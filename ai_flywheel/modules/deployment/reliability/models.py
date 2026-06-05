"""Reliability & Incident Engine — SQLAlchemy models.

Incident: Tracks production incidents with severity and resolution.
HealthMetric: Records health metrics with threshold monitoring.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class Incident(BaseModel, VentureScopedMixin):
    """A production incident with lifecycle tracking."""

    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String, nullable=False
    )  # critical | high | medium | low
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="open"
    )  # open | investigating | mitigating | resolved
    source_module: Mapped[str | None] = mapped_column(String, nullable=True)
    affected_deployments: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    detection_method: Mapped[str] = mapped_column(
        String, nullable=False, default="manual"
    )  # monitor | alert | manual | automated
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)


class HealthMetric(BaseModel, VentureScopedMixin):
    """A health metric data point with threshold monitoring."""

    __tablename__ = "health_metrics"

    deployment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    metric_name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_warning: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_critical: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="healthy"
    )  # healthy | warning | critical
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
