# ruff: noqa: E501
"""Unit tests for the Reliability & Incident Engine service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.deployment.reliability.schemas import (
    IncidentCreate,
    RecordMetricRequest,
)
from ai_flywheel.modules.deployment.reliability.service import (
    ReliabilityEngine,
)


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


def _make_incident(
    id_="inc-1",
    title="Service Down",
    severity="high",
    status="open",
    started_at=None,
    resolved_at=None,
    duration_minutes=None,
):
    """Create a mock Incident ORM object."""
    inc = MagicMock()
    inc.id = id_
    inc.venture_id = "ven-1"
    inc.title = title
    inc.description = "Service is not responding"
    inc.severity = severity
    inc.status = status
    inc.source_module = "api_gateway"
    inc.affected_deployments = ["dep-1"]
    inc.detection_method = "manual"
    inc.resolution = None if status != "resolved" else "Fixed config"
    inc.started_at = started_at or datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
    inc.resolved_at = resolved_at
    inc.duration_minutes = duration_minutes
    inc.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    inc.deleted_at = None
    return inc


def _make_metric(
    id_="met-1",
    metric_name="cpu_usage",
    value=45.0,
    status="healthy",
):
    """Create a mock HealthMetric ORM object."""
    met = MagicMock()
    met.id = id_
    met.venture_id = "ven-1"
    met.deployment_id = "dep-1"
    met.metric_name = metric_name
    met.value = value
    met.threshold_warning = 70.0
    met.threshold_critical = 90.0
    met.status = status
    met.recorded_at = datetime(2024, 6, 1, tzinfo=UTC)
    met.deleted_at = None
    return met


@pytest.mark.asyncio
async def test_create_incident(mock_session, mock_event_bus):
    """Test creating an incident."""
    engine = ReliabilityEngine()

    data = IncidentCreate(
        title="Database Connection Timeout",
        description="DB pool exhausted",
        severity="high",
        source_module="data_service",
        affected_deployments=["dep-1"],
        detection_method="monitor",
    )

    with (
        patch("ai_flywheel.modules.deployment.reliability.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.deployment.reliability.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        def capture_add(obj):
            obj.id = "inc-new"
            obj.venture_id = "ven-1"
            obj.title = data.title
            obj.description = data.description
            obj.severity = data.severity
            obj.status = "open"
            obj.source_module = data.source_module
            obj.affected_deployments = data.affected_deployments
            obj.detection_method = data.detection_method
            obj.resolution = None
            obj.started_at = datetime(2024, 6, 1, tzinfo=UTC)
            obj.resolved_at = None
            obj.duration_minutes = None
            obj.created_at = datetime(2024, 6, 1, tzinfo=UTC)

        mock_session.add.side_effect = capture_add

        result = await engine.create_incident("ven-1", data)

    assert result.title == "Database Connection Timeout"
    assert result.severity == "high"
    assert result.status == "open"
    mock_event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_incident(mock_session, mock_event_bus):
    """Test resolving an incident sets status, resolution, and duration."""
    engine = ReliabilityEngine()

    incident = _make_incident(started_at=datetime(2024, 6, 1, 10, 0, tzinfo=UTC))
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = incident
    mock_session.execute.return_value = mock_result

    with (
        patch("ai_flywheel.modules.deployment.reliability.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.deployment.reliability.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        await engine.resolve_incident("ven-1", "inc-1", "Restarted service")

    assert incident.status == "resolved"
    assert incident.resolution == "Restarted service"
    assert incident.resolved_at is not None
    assert incident.duration_minutes is not None
    mock_event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_record_metric_healthy(mock_session, mock_event_bus):
    """Test recording a metric within healthy thresholds."""
    engine = ReliabilityEngine()

    request = RecordMetricRequest(
        deployment_id="dep-1",
        metric_name="cpu_usage",
        value=45.0,
        threshold_warning=70.0,
        threshold_critical=90.0,
    )

    with (
        patch("ai_flywheel.modules.deployment.reliability.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.deployment.reliability.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        def capture_add(obj):
            obj.id = "met-new"
            obj.deployment_id = request.deployment_id
            obj.metric_name = request.metric_name
            obj.value = request.value
            obj.status = "healthy"
            obj.threshold_warning = request.threshold_warning
            obj.threshold_critical = request.threshold_critical
            obj.recorded_at = datetime(2024, 6, 1, tzinfo=UTC)

        mock_session.add.side_effect = capture_add

        result = await engine.record_metric("ven-1", request)

    assert result.metric_name == "cpu_usage"
    assert result.value == 45.0
    assert result.status == "healthy"
    # Only metric.recorded event, no incident created
    assert mock_event_bus.publish.call_count == 1


@pytest.mark.asyncio
async def test_record_metric_auto_incident(mock_session, mock_event_bus):
    """Test that recording a metric above critical threshold auto-creates an incident."""
    engine = ReliabilityEngine()

    request = RecordMetricRequest(
        deployment_id="dep-1",
        metric_name="cpu_usage",
        value=95.0,
        threshold_warning=70.0,
        threshold_critical=90.0,
    )

    add_calls = []

    with (
        patch("ai_flywheel.modules.deployment.reliability.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.deployment.reliability.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        def capture_add(obj):
            add_calls.append(obj)
            if hasattr(obj, "metric_name"):
                # It's a HealthMetric
                obj.id = "met-new"
                obj.deployment_id = request.deployment_id
                obj.metric_name = request.metric_name
                obj.value = request.value
                obj.status = "critical"
                obj.threshold_warning = request.threshold_warning
                obj.threshold_critical = request.threshold_critical
                obj.recorded_at = datetime(2024, 6, 1, tzinfo=UTC)

        mock_session.add.side_effect = capture_add

        result = await engine.record_metric("ven-1", request)

    assert result.status == "critical"
    # Should have created both metric and incident (2 add calls)
    assert len(add_calls) == 2
    # 3 events: metric.recorded, metric.threshold.breached, incident.created
    assert mock_event_bus.publish.call_count == 3


@pytest.mark.asyncio
async def test_get_report(mock_session):
    """Test reliability report aggregation."""
    engine = ReliabilityEngine()

    incidents = [
        _make_incident("inc-1", status="resolved", duration_minutes=30.0),
        _make_incident("inc-2", status="resolved", duration_minutes=60.0),
        _make_incident("inc-3", status="open"),
    ]
    metrics = [
        _make_metric("met-1", status="healthy"),
        _make_metric("met-2", status="healthy"),
        _make_metric("met-3", status="warning"),
        _make_metric("met-4", status="critical"),
    ]

    # Configure execute to return incidents first, then metrics
    incident_result = MagicMock()
    incident_result.scalars.return_value.all.return_value = incidents
    metric_result = MagicMock()
    metric_result.scalars.return_value.all.return_value = metrics

    mock_session.execute.side_effect = [incident_result, metric_result]

    with patch("ai_flywheel.modules.deployment.reliability.service.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

        report = await engine.get_report("ven-1")

    assert report.venture_id == "ven-1"
    assert report.total_incidents == 3
    assert report.open_incidents == 1
    assert report.mttr_minutes == 45.0  # (30 + 60) / 2
    assert report.metrics_healthy == 2
    assert report.metrics_warning == 1
    assert report.metrics_critical == 1
    assert report.uptime_pct == 75.0  # 3/4 non-critical
