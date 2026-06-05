"""Data Quality Engine — SQLAlchemy models.

QualityReport: Persisted results of a quality check run.
QualityRule: Configurable validation rules scoped to a venture.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class QualityReport(BaseModel, VentureScopedMixin):
    """Persisted result of a data quality check."""

    __tablename__ = "quality_reports"

    source_id: Mapped[str | None] = mapped_column(String, nullable=True)
    dataset_name: Mapped[str] = mapped_column(String, nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_records: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid_records: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False)
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    issues: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    field_profiles: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    run_duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class QualityRule(BaseModel, VentureScopedMixin):
    """A configurable data validation rule."""

    __tablename__ = "quality_rules"

    name: Mapped[str] = mapped_column(String, nullable=False)
    rule_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # not_null | type_check | range | regex | unique | custom
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    severity: Mapped[str] = mapped_column(
        String, nullable=False, default="error"
    )  # error | warning | info
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
