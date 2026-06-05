# ruff: noqa: E501
"""SQLAlchemy models for Model Forge."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class ModelDefinition(BaseModel, VentureScopedMixin):
    """An ML model definition with configuration and training state."""

    __tablename__ = "model_definitions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # classifier | regressor | ranker | embedder | custom
    framework: Mapped[str] = mapped_column(
        String(50), nullable=False, default="sklearn"
    )  # sklearn | custom
    algorithm: Mapped[str] = mapped_column(
        String(100), nullable=False, default="logistic_regression"
    )  # logistic_regression | random_forest | gradient_boost | svm | linear | custom
    hyperparameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    feature_set_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft | training | trained | deployed | archived
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    training_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_samples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class TrainingRun(BaseModel, VentureScopedMixin):
    """A single training run for a model."""

    __tablename__ = "training_runs"

    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_definitions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )  # running | completed | failed
    hyperparameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {accuracy, precision, recall, f1, mse, mae, r2}
    training_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
