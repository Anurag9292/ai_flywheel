"""SQLAlchemy models for A/B Test & Optimization Engine.

Experiment: Defines an experiment with variants, metrics, and traffic splits.
ExperimentObservation: Individual data points collected per variant.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class Experiment(BaseModel, VentureScopedMixin):
    """An experiment (A/B test, bandit, or multivariate) for a venture."""

    __tablename__ = "ab_experiments"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )  # "draft" | "running" | "paused" | "completed" | "cancelled"
    experiment_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ab_test"
    )  # "ab_test" | "bandit" | "multivariate"
    variants: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # list of {name, description, is_control}
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="conversion"
    )  # "conversion" | "continuous" | "count"
    traffic_split: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # {variant_name: percentage}
    sample_size_target: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    current_sample_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    winner: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    confidence_level: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.95
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class ExperimentObservation(BaseModel, VentureScopedMixin):
    """A single observation/data point for an experiment variant."""

    __tablename__ = "ab_experiment_observations"

    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ab_experiments.id"), nullable=False, index=True
    )
    variant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
