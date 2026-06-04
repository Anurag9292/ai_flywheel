"""Trace models for distributed observability."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class TraceSpan(BaseModel, VentureScopedMixin):
    """A single span in a distributed trace."""

    __tablename__ = "trace_spans"

    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # What happened
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Cost tracking
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Payload
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
