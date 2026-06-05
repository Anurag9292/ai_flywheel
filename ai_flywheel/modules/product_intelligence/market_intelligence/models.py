"""Market & Signal Intelligence — SQLAlchemy models.

Module #25: Tracks signal sources, detected market signals, and synthesized reports.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class SignalSource(BaseModel, VentureScopedMixin):
    """A configured source for market signal scanning."""

    __tablename__ = "market_signal_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="news|social|jobs|patents|regulatory|funding|custom",
    )
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class MarketSignal(BaseModel, VentureScopedMixin):
    """A detected market signal with relevance and impact scoring."""

    __tablename__ = "market_signals"

    source_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("market_signal_sources.id"),
        nullable=True,
    )
    signal_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="competitor_move|trend|funding|launch|regulatory|opportunity|threat",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(
        Float, nullable=False, comment="0.0 to 1.0"
    )
    impact_score: Mapped[float] = mapped_column(
        Float, nullable=False, comment="0.0 to 1.0"
    )
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketReport(BaseModel, VentureScopedMixin):
    """A synthesized market intelligence report."""

    __tablename__ = "market_reports"

    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="digest|competitor|trend|opportunity",
    )
    period: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    signals_analyzed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    key_findings: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    recommendations: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
