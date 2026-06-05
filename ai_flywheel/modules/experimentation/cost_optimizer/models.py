"""SQLAlchemy models for Cost Optimizer — budgets and alerts.

Budget: Defines spending limits per venture per period (daily/weekly/monthly).
CostAlert: Records when a venture approaches or exceeds its budget.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class Budget(BaseModel, VentureScopedMixin):
    """Spending limit for a venture over a specific time period."""

    __tablename__ = "cost_budgets"

    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "daily" | "weekly" | "monthly"
    limit_usd: Mapped[float] = mapped_column(Float, nullable=False)
    alert_threshold_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.8
    )  # Alert at 80% by default
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CostAlert(BaseModel, VentureScopedMixin):
    """Alert generated when spending approaches or exceeds a budget."""

    __tablename__ = "cost_alerts"

    alert_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "threshold" | "exceeded" | "anomaly"
    budget_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cost_budgets.id"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    current_spend_usd: Mapped[float] = mapped_column(Float, nullable=False)
    limit_usd: Mapped[float] = mapped_column(Float, nullable=False)
    period: Mapped[str] = mapped_column(String(50), nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
