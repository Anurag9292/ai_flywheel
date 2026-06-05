"""Pydantic schemas for Meta-Learning & Flywheel Engine."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RecordMetricRequest(BaseModel):
    """Request to record a flywheel metric."""

    venture_id: str
    metric_name: str
    value: float
    period: str


class FlywheelMetricResponse(BaseModel):
    """Metric data returned to clients."""

    id: str
    venture_id: str
    metric_name: str
    value: float
    period: str
    recorded_at: datetime


class VelocityReport(BaseModel):
    """Velocity report for a single venture."""

    venture_id: str
    metrics: list[dict]
    velocity_score: float
    trend: str  # "accelerating"|"decelerating"|"stable"
    comparison_to_previous: float | None


class InsightResponse(BaseModel):
    """Cross-venture insight data."""

    id: str
    insight_type: str
    title: str
    description: str
    evidence: dict
    confidence: float
    affected_ventures: list[str]
    generated_at: datetime


class FlywheelReport(BaseModel):
    """Cross-venture flywheel summary."""

    total_ventures: int
    avg_velocity: float
    fastest_venture: dict | None
    slowest_venture: dict | None
    recent_insights: list[InsightResponse]
    acceleration_trend: str  # "accelerating"|"decelerating"|"stable"
