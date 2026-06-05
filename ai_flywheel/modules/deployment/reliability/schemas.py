"""Reliability & Incident Engine — Pydantic schemas for API layer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    """Request to create a new incident."""

    title: str
    description: str = ""
    severity: str  # critical | high | medium | low
    source_module: str | None = None
    affected_deployments: list[str] = Field(default_factory=list)
    detection_method: str = "manual"


class IncidentResponse(BaseModel):
    """Full incident metadata response."""

    id: str
    venture_id: str
    title: str
    description: str | None
    severity: str
    status: str
    source_module: str | None
    affected_deployments: list[str]
    detection_method: str
    resolution: str | None
    started_at: datetime
    resolved_at: datetime | None
    duration_minutes: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    """Request to update an incident."""

    status: str | None = None
    resolution: str | None = None


class RecordMetricRequest(BaseModel):
    """Request to record a health metric."""

    deployment_id: str | None = None
    metric_name: str
    value: float
    threshold_warning: float | None = None
    threshold_critical: float | None = None


class MetricResponse(BaseModel):
    """Health metric data point response."""

    id: str
    deployment_id: str | None
    metric_name: str
    value: float
    status: str
    threshold_warning: float | None
    threshold_critical: float | None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class ReliabilityReport(BaseModel):
    """Aggregate reliability report for a venture."""

    venture_id: str
    total_incidents: int
    open_incidents: int
    mttr_minutes: float | None
    uptime_pct: float
    metrics_healthy: int
    metrics_warning: int
    metrics_critical: int
