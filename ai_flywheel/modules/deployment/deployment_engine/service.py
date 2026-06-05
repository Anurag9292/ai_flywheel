# ruff: noqa: E501
"""Deployment Engine — core service.

Manages multi-target deployments with version management, rollback support,
health checks, and a full event audit trail.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus

from .models import Deployment, DeploymentEvent
from .schemas import (
    DeploymentCreate,
    DeploymentResponse,
    DeployRequest,
    DeployResult,
    HealthCheckResult,
    RollbackRequest,
    RollbackResult,
)

logger = structlog.get_logger()


class DeploymentEngine:
    """Manages deployments, rollbacks, health checks, and event audit trails."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_deployment(
        self, venture_id: str, data: DeploymentCreate
    ) -> DeploymentResponse:
        """Create a new deployment."""
        async with get_session(venture_id) as session:
            deployment = Deployment(
                venture_id=venture_id,
                name=data.name,
                target=data.target,
                config=data.config,
                status="pending",
                version=1,
            )
            session.add(deployment)
            await session.flush()
            await session.refresh(deployment)

            # Record creation event
            event = DeploymentEvent(
                venture_id=venture_id,
                deployment_id=deployment.id,
                event_type="created",
                details={"name": data.name, "target": data.target},
                occurred_at=datetime.now(UTC),
            )
            session.add(event)
            await session.flush()

            logger.info(
                "deployment_created",
                venture_id=venture_id,
                deployment_id=deployment.id,
                name=data.name,
                target=data.target,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="deployment.created",
                source_module="deployment_engine",
                payload={
                    "deployment_id": deployment.id,
                    "name": data.name,
                    "target": data.target,
                },
                venture_id=venture_id,
            )

            return self._to_response(deployment)

    async def get_deployment(self, venture_id: str, deployment_id: str) -> DeploymentResponse:
        """Get a single deployment by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Deployment).where(
                    Deployment.venture_id == venture_id,
                    Deployment.id == deployment_id,
                    Deployment.deleted_at.is_(None),
                )
            )
            deployment = result.scalar_one()
            return self._to_response(deployment)

    async def list_deployments(self, venture_id: str) -> list[DeploymentResponse]:
        """List all deployments for a venture."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Deployment).where(
                    Deployment.venture_id == venture_id,
                    Deployment.deleted_at.is_(None),
                )
            )
            deployments = result.scalars().all()
            return [self._to_response(d) for d in deployments]

    # ------------------------------------------------------------------
    # Deploy
    # ------------------------------------------------------------------

    async def deploy(
        self, venture_id: str, request: DeployRequest
    ) -> DeployResult:
        """Trigger a deployment — simulates build, deploy, and activation."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Deployment).where(
                    Deployment.venture_id == venture_id,
                    Deployment.id == request.deployment_id,
                    Deployment.deleted_at.is_(None),
                )
            )
            deployment = result.scalar_one()

            events_recorded: list[str] = []
            now = datetime.now(UTC)

            # Building phase
            deployment.status = "building"
            build_event = DeploymentEvent(
                venture_id=venture_id,
                deployment_id=deployment.id,
                event_type="building",
                details={"version": deployment.version},
                occurred_at=now,
            )
            session.add(build_event)
            events_recorded.append("building")

            # Deploy phase
            deployment.status = "deploying"
            new_version = request.version if request.version else deployment.version + 1
            deployment.previous_version_id = deployment.id
            deployment.version = new_version
            deployment.deployed_at = now
            deployment.status = "active"
            deployment.url = f"https://{deployment.name}.deploy.example.com/v{new_version}"
            deployment.health_check_url = f"https://{deployment.name}.deploy.example.com/v{new_version}/health"

            deploy_event = DeploymentEvent(
                venture_id=venture_id,
                deployment_id=deployment.id,
                event_type="deployed",
                details={"version": new_version, "url": deployment.url},
                occurred_at=now,
            )
            session.add(deploy_event)
            events_recorded.append("deployed")

            # Health check passed
            health_event = DeploymentEvent(
                venture_id=venture_id,
                deployment_id=deployment.id,
                event_type="health_check_passed",
                details={"status_code": 200},
                occurred_at=now,
            )
            session.add(health_event)
            events_recorded.append("health_check_passed")

            await session.flush()

            logger.info(
                "deployment_deployed",
                venture_id=venture_id,
                deployment_id=deployment.id,
                version=new_version,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="deployment.started",
                source_module="deployment_engine",
                payload={"deployment_id": deployment.id, "version": new_version},
                venture_id=venture_id,
            )
            await event_bus.publish(
                event_type="deployment.completed",
                source_module="deployment_engine",
                payload={"deployment_id": deployment.id, "version": new_version, "url": deployment.url},
                venture_id=venture_id,
            )

            return DeployResult(
                deployment_id=deployment.id,
                status="active",
                url=deployment.url,
                version=new_version,
                events=events_recorded,
            )

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    async def rollback(
        self, venture_id: str, request: RollbackRequest
    ) -> RollbackResult:
        """Rollback a deployment to the previous version."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Deployment).where(
                    Deployment.venture_id == venture_id,
                    Deployment.id == request.deployment_id,
                    Deployment.deleted_at.is_(None),
                )
            )
            deployment = result.scalar_one()

            previous_version = max(1, deployment.version - 1)
            now = datetime.now(UTC)

            deployment.status = "rolled_back"
            deployment.version = previous_version
            deployment.rolled_back_at = now
            deployment.url = f"https://{deployment.name}.deploy.example.com/v{previous_version}"

            rollback_event = DeploymentEvent(
                venture_id=venture_id,
                deployment_id=deployment.id,
                event_type="rolled_back",
                details={"rolled_back_to_version": previous_version},
                occurred_at=now,
            )
            session.add(rollback_event)
            await session.flush()

            logger.info(
                "deployment_rolled_back",
                venture_id=venture_id,
                deployment_id=deployment.id,
                version=previous_version,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="deployment.rolled_back",
                source_module="deployment_engine",
                payload={"deployment_id": deployment.id, "version": previous_version},
                venture_id=venture_id,
            )

            return RollbackResult(
                deployment_id=deployment.id,
                rolled_back_to_version=previous_version,
                status="rolled_back",
            )

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    async def health_check(
        self, venture_id: str, deployment_id: str
    ) -> HealthCheckResult:
        """Check if a deployment is healthy (simulated: always healthy)."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Deployment).where(
                    Deployment.venture_id == venture_id,
                    Deployment.id == deployment_id,
                    Deployment.deleted_at.is_(None),
                )
            )
            deployment = result.scalar_one()

            now = datetime.now(UTC)

            # Simulated health check — always returns healthy
            health_event = DeploymentEvent(
                venture_id=venture_id,
                deployment_id=deployment.id,
                event_type="health_check_passed",
                details={"status_code": 200, "latency_ms": 45.0},
                occurred_at=now,
            )
            session.add(health_event)
            await session.flush()

            return HealthCheckResult(
                deployment_id=deployment.id,
                healthy=True,
                status_code=200,
                latency_ms=45.0,
                checked_at=now.isoformat(),
            )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    async def get_events(self, venture_id: str, deployment_id: str) -> list[dict[str, Any]]:
        """Get all events for a deployment."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(DeploymentEvent).where(
                    DeploymentEvent.venture_id == venture_id,
                    DeploymentEvent.deployment_id == deployment_id,
                    DeploymentEvent.deleted_at.is_(None),
                )
            )
            events = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "details": e.details,
                    "occurred_at": e.occurred_at.isoformat(),
                }
                for e in events
            ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_response(self, deployment: Deployment) -> DeploymentResponse:
        """Convert ORM model to response schema."""
        return DeploymentResponse(
            id=deployment.id,
            venture_id=deployment.venture_id,
            name=deployment.name,
            target=deployment.target,
            status=deployment.status,
            config=deployment.config,
            version=deployment.version,
            url=deployment.url,
            health_check_url=deployment.health_check_url,
            deployed_at=deployment.deployed_at,
            created_at=deployment.created_at,
        )
