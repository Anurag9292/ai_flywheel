"""Pydantic schemas for Cost Optimizer — request/response validation.

Defines the API contract for budgets, alerts, reports, and trends.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    """Schema for creating a new budget."""

    venture_id: str
    period_type: str = Field(..., pattern=r"^(daily|weekly|monthly)$")
    limit_usd: float = Field(..., gt=0)
    alert_threshold_pct: float = Field(default=0.8, ge=0.0, le=1.0)


class BudgetUpdate(BaseModel):
    """Schema for updating an existing budget. All fields optional."""

    limit_usd: float | None = Field(default=None, gt=0)
    alert_threshold_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    is_active: bool | None = None


class BudgetResponse(BaseModel):
    """Schema for budget responses."""

    id: str
    venture_id: str
    period_type: str
    limit_usd: float
    alert_threshold_pct: float
    current_spend_usd: float = 0.0
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CostAlertResponse(BaseModel):
    """Schema for cost alert responses."""

    id: str
    venture_id: str
    alert_type: str
    message: str
    current_spend_usd: float
    limit_usd: float
    period: str
    acknowledged: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CostReport(BaseModel):
    """Aggregated cost report for a venture over a period."""

    venture_id: str
    period: str
    total_usd: float
    by_module: dict[str, float]
    by_provider: dict[str, float]
    by_model: dict[str, float]
    top_operations: list[dict[str, Any]]
    budget_utilization_pct: float | None = None


class CostTrend(BaseModel):
    """Spending trend across multiple periods."""

    venture_id: str
    periods: list[dict[str, Any]]
    trend_direction: str  # "increasing" | "decreasing" | "stable"
    projected_monthly: float
