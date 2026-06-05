# ruff: noqa: E501
"""Deployment Engine — SQLAlchemy models.

Deployment: A deployment target with version, status, and rollback support.
DeploymentEvent: An audit trail event for deployment lifecycle.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_flywheel.core.models.base import BaseModel, VentureScopedMixin


class Deployment(BaseModel, VentureScopedMixin):
    """A deployment to a target platform."""

    __tablename__ = "deployments"

    name: Mapped[str] = mapped_column(String, nullable=False)
    target: Mapped[str] = mapped_column(
        String, nullable=False
    )  # vercel | fly | cloudflare | docker | custom
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )  # pending | building | deploying | active | failed | rolled_back
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # env_vars, scaling, region
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    health_check_url: Mapped[str | None] = mapped_column(String, nullable=True)
    previous_version_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # for rollback
    deployed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rolled_back_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DeploymentEvent(BaseModel, VentureScopedMixin):
    """An event in the deployment lifecycle audit trail."""

    __tablename__ = "deployment_events"

    deployment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deployments.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # created | building | deployed | health_check_passed | health_check_failed | rolled_back | scaled
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
