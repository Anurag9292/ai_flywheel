"""Evaluation Framework — SQLAlchemy models.

EvalSuite: A collection of test cases and metrics for evaluating a target module.
EvalRun: A single execution of an eval suite with scored results.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class EvalSuite(BaseModel, VentureScopedMixin):
    """A collection of test cases and metrics for evaluating a target module."""

    __tablename__ = "eval_suites"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_module: Mapped[str] = mapped_column(String, nullable=False)
    metrics: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    test_cases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="active"
    )  # active | archived
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class EvalRun(BaseModel, VentureScopedMixin):
    """A single execution of an eval suite with scored results."""

    __tablename__ = "eval_runs"

    suite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("eval_suites.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="running"
    )  # running | completed | failed
    scores: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # {overall, per_metric: {}, per_case: []}
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # model/agent/prompt version tested
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
