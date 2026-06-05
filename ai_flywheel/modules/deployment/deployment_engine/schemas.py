"""Deployment Engine — Pydantic schemas for API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DeploymentCreate(BaseModel):
    """Request to create a new deployment."""

    name: str
    target: str  # vercel | fly | cloudflare | docker | custom
    config: dict[str, Any] = Field(default_factory=dict)


class DeploymentResponse(BaseModel):
    """Full deployment metadata response."""

    id: str
    venture_id: str
    name: str
    target: str
    status: str
    config: dict[str, Any]
    version: int
    url: str | None
    health_check_url: str | None
    deployed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeployRequest(BaseModel):
    """Request to trigger a deployment."""

    deployment_id: str
    version: int | None = None


class DeployResult(BaseModel):
    """Result of a deployment action."""

    deployment_id: str
    status: str
    url: str | None
    version: int
    events: list[str]


class RollbackRequest(BaseModel):
    """Request to rollback a deployment."""

    deployment_id: str


class RollbackResult(BaseModel):
    """Result of a rollback action."""

    deployment_id: str
    rolled_back_to_version: int
    status: str


class HealthCheckResult(BaseModel):
    """Result of a health check."""

    deployment_id: str
    healthy: bool
    status_code: int | None
    latency_ms: float | None
    checked_at: str
