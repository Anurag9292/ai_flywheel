# ruff: noqa: E501
"""Reliability & Incident Engine — core service.

Manages incident lifecycle, records health metrics with threshold monitoring,
auto-creates incidents on critical threshold breaches, and provides reliability reporting.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus

from .models import HealthMetric, Incident
from .schemas import (
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
    MetricResponse,
    RecordMetricRequest,
    ReliabilityReport,
)

logger = structlog.get_logger()


class ReliabilityEngine:
    """Manages incidents, health metrics, and reliability reporting."""

    # ------------------------------------------------------------------
    # Incident CRUD
    # ------------------------------------------------------------------

    async def create_incident(
        self, venture_id: str, data: IncidentCreate
    ) -> IncidentResponse:
        """Create a new incident."""
        async with get_session(venture_id) as session:
            now = datetime.now(UTC)
            incident = Incident(
                venture_id=venture_id,
                title=data.title,
                description=data.description,
                severity=data.severity,
                status="open",
                source_module=data.source_module,
                affected_deployments=data.affected_deployments,
                detection_method=data.detection_method,
                started_at=now,
            )
            session.add(incident)
            await session.flush()
            await session.refresh(incident)

            logger.info(
                "incident_created",
                venture_id=venture_id,
                incident_id=incident.id,
                title=data.title,
                severity=data.severity,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="incident.created",
                source_module="reliability_engine",
                payload={
                    "incident_id": incident.id,
                    "title": data.title,
                    "severity": data.severity,
                },
                venture_id=venture_id,
            )

            return self._incident_to_response(incident)

    async def get_incident(self, venture_id: str, incident_id: str) -> IncidentResponse:
        """Get a single incident by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Incident).where(
                    Incident.venture_id == venture_id,
                    Incident.id == incident_id,
                    Incident.deleted_at.is_(None),
                )
            )
            incident = result.scalar_one()
            return self._incident_to_response(incident)

    async def list_incidents(
        self, venture_id: str, status: str | None = None
    ) -> list[IncidentResponse]:
        """List incidents for a venture, optionally filtered by status."""
        async with get_session(venture_id) as session:
            query = select(Incident).where(
                Incident.venture_id == venture_id,
                Incident.deleted_at.is_(None),
            )
            if status:
                query = query.where(Incident.status == status)
            result = await session.execute(query)
            incidents = result.scalars().all()
            return [self._incident_to_response(i) for i in incidents]

    async def update_incident(
        self, venture_id: str, incident_id: str, data: IncidentUpdate
    ) -> IncidentResponse:
        """Update an incident's status or resolution."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Incident).where(
                    Incident.venture_id == venture_id,
                    Incident.id == incident_id,
                    Incident.deleted_at.is_(None),
                )
            )
            incident = result.scalar_one()

            if data.status is not None:
                incident.status = data.status
            if data.resolution is not None:
                incident.resolution = data.resolution

            await session.flush()
            return self._incident_to_response(incident)

    async def resolve_incident(
        self, venture_id: str, incident_id: str, resolution: str
    ) -> IncidentResponse:
        """Resolve an incident with a resolution message."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Incident).where(
                    Incident.venture_id == venture_id,
                    Incident.id == incident_id,
                    Incident.deleted_at.is_(None),
                )
            )
            incident = result.scalar_one()

            now = datetime.now(UTC)
            incident.status = "resolved"
            incident.resolution = resolution
            incident.resolved_at = now

            # Calculate duration
            if incident.started_at:
                delta = now - incident.started_at
                incident.duration_minutes = delta.total_seconds() / 60.0

            await session.flush()

            logger.info(
                "incident_resolved",
                venture_id=venture_id,
                incident_id=incident.id,
                duration_minutes=incident.duration_minutes,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="incident.resolved",
                source_module="reliability_engine",
                payload={
                    "incident_id": incident.id,
                    "resolution": resolution,
                    "duration_minutes": incident.duration_minutes,
                },
                venture_id=venture_id,
            )

            return self._incident_to_response(incident)

    # ------------------------------------------------------------------
    # Health Metrics
    # ------------------------------------------------------------------

    async def record_metric(
        self, venture_id: str, request: RecordMetricRequest
    ) -> MetricResponse:
        """Record a health metric, check thresholds, and auto-create incident if critical."""
        async with get_session(venture_id) as session:
            now = datetime.now(UTC)

            # Determine metric status based on thresholds
            status = "healthy"
            if request.threshold_critical is not None and request.value >= request.threshold_critical:
                status = "critical"
            elif request.threshold_warning is not None and request.value >= request.threshold_warning:
                status = "warning"

            metric = HealthMetric(
                venture_id=venture_id,
                deployment_id=request.deployment_id,
                metric_name=request.metric_name,
                value=request.value,
                threshold_warning=request.threshold_warning,
                threshold_critical=request.threshold_critical,
                status=status,
                recorded_at=now,
            )
            session.add(metric)
            await session.flush()
            await session.refresh(metric)

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="metric.recorded",
                source_module="reliability_engine",
                payload={
                    "metric_id": metric.id,
                    "metric_name": request.metric_name,
                    "value": request.value,
                    "status": status,
                },
                venture_id=venture_id,
            )

            # Auto-create incident if critical threshold breached
            if status == "critical":
                await event_bus.publish(
                    event_type="metric.threshold.breached",
                    source_module="reliability_engine",
                    payload={
                        "metric_id": metric.id,
                        "metric_name": request.metric_name,
                        "value": request.value,
                        "threshold": request.threshold_critical,
                    },
                    venture_id=venture_id,
                )

                incident = Incident(
                    venture_id=venture_id,
                    title=f"Critical threshold breached: {request.metric_name}",
                    description=f"Metric {request.metric_name} reached {request.value} (threshold: {request.threshold_critical})",
                    severity="high",
                    status="open",
                    source_module="reliability_engine",
                    affected_deployments=[request.deployment_id] if request.deployment_id else [],
                    detection_method="automated",
                    started_at=now,
                )
                session.add(incident)
                await session.flush()

                await event_bus.publish(
                    event_type="incident.created",
                    source_module="reliability_engine",
                    payload={
                        "incident_id": incident.id,
                        "title": incident.title,
                        "severity": "high",
                        "auto_created": True,
                    },
                    venture_id=venture_id,
                )

                logger.info(
                    "auto_incident_created",
                    venture_id=venture_id,
                    incident_id=incident.id,
                    metric_name=request.metric_name,
                    value=request.value,
                )

            return self._metric_to_response(metric)

    async def get_metrics(
        self, venture_id: str, deployment_id: str | None = None
    ) -> list[MetricResponse]:
        """Get health metrics, optionally filtered by deployment."""
        async with get_session(venture_id) as session:
            query = select(HealthMetric).where(
                HealthMetric.venture_id == venture_id,
                HealthMetric.deleted_at.is_(None),
            )
            if deployment_id:
                query = query.where(HealthMetric.deployment_id == deployment_id)
            result = await session.execute(query)
            metrics = result.scalars().all()
            return [self._metric_to_response(m) for m in metrics]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def get_report(self, venture_id: str) -> ReliabilityReport:
        """Generate an aggregate reliability report for a venture."""
        async with get_session(venture_id) as session:
            # Get all incidents
            incident_result = await session.execute(
                select(Incident).where(
                    Incident.venture_id == venture_id,
                    Incident.deleted_at.is_(None),
                )
            )
            incidents = incident_result.scalars().all()

            total_incidents = len(incidents)
            open_incidents = sum(1 for i in incidents if i.status != "resolved")

            # Calculate MTTR for resolved incidents
            resolved = [i for i in incidents if i.status == "resolved" and i.duration_minutes is not None]
            mttr = None
            if resolved:
                mttr = sum(i.duration_minutes for i in resolved) / len(resolved)

            # Get metrics
            metric_result = await session.execute(
                select(HealthMetric).where(
                    HealthMetric.venture_id == venture_id,
                    HealthMetric.deleted_at.is_(None),
                )
            )
            metrics = metric_result.scalars().all()

            metrics_healthy = sum(1 for m in metrics if m.status == "healthy")
            metrics_warning = sum(1 for m in metrics if m.status == "warning")
            metrics_critical = sum(1 for m in metrics if m.status == "critical")

            # Uptime calculation: proportion of non-critical metrics
            total_metrics = len(metrics)
            uptime_pct = ((total_metrics - metrics_critical) / total_metrics * 100.0) if total_metrics > 0 else 100.0

            return ReliabilityReport(
                venture_id=venture_id,
                total_incidents=total_incidents,
                open_incidents=open_incidents,
                mttr_minutes=mttr,
                uptime_pct=round(uptime_pct, 2),
                metrics_healthy=metrics_healthy,
                metrics_warning=metrics_warning,
                metrics_critical=metrics_critical,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _incident_to_response(self, incident: Incident) -> IncidentResponse:
        """Convert ORM model to response schema."""
        return IncidentResponse(
            id=incident.id,
            venture_id=incident.venture_id,
            title=incident.title,
            description=incident.description,
            severity=incident.severity,
            status=incident.status,
            source_module=incident.source_module,
            affected_deployments=incident.affected_deployments,
            detection_method=incident.detection_method,
            resolution=incident.resolution,
            started_at=incident.started_at,
            resolved_at=incident.resolved_at,
            duration_minutes=incident.duration_minutes,
            created_at=incident.created_at,
        )

    def _metric_to_response(self, metric: HealthMetric) -> MetricResponse:
        """Convert ORM model to response schema."""
        return MetricResponse(
            id=metric.id,
            deployment_id=metric.deployment_id,
            metric_name=metric.metric_name,
            value=metric.value,
            status=metric.status,
            threshold_warning=metric.threshold_warning,
            threshold_critical=metric.threshold_critical,
            recorded_at=metric.recorded_at,
        )
