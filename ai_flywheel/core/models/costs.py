"""Cost tracking model — records every paid operation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class CostRecord(BaseModel, VentureScopedMixin):
    """Records the cost of a single billable operation."""

    __tablename__ = "cost_records"

    module_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(255), nullable=False)
    trace_span_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Cost
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Token usage
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Context
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
