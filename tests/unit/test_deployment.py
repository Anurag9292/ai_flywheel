# ruff: noqa: E501
"""Unit tests for the Deployment Engine service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.deployment.deployment_engine.schemas import (
    DeploymentCreate,
    DeployRequest,
    RollbackRequest,
)
from ai_flywheel.modules.deployment.deployment_engine.service import (
    DeploymentEngine,
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


def _make_deployment(
    id_="dep-1",
    name="my-app",
    target="fly",
    status="pending",
    version=1,
):
    """Create a mock Deployment ORM object."""
    dep = MagicMock()
    dep.id = id_
    dep.venture_id = "ven-1"
    dep.name = name
    dep.target = target
    dep.status = status
    dep.config = {"region": "us-east-1"}
    dep.version = version
    dep.url = None
    dep.health_check_url = None
    dep.previous_version_id = None
    dep.deployed_at = None
    dep.rolled_back_at = None
    dep.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    dep.deleted_at = None
    return dep


def _make_event(id_="evt-1", event_type="created"):
    """Create a mock DeploymentEvent ORM object."""
    evt = MagicMock()
    evt.id = id_
    evt.venture_id = "ven-1"
    evt.deployment_id = "dep-1"
    evt.event_type = event_type
    evt.details = {"name": "my-app"}
    evt.occurred_at = datetime(2024, 6, 1, tzinfo=UTC)
    evt.deleted_at = None
    return evt


@pytest.mark.asyncio
async def test_create_deployment(mock_session, mock_event_bus):
    """Test creating a deployment."""
    engine = DeploymentEngine()

    data = DeploymentCreate(name="my-app", target="fly", config={"region": "us-east-1"})

    with (
        patch("ai_flywheel.modules.deployment.deployment_engine.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.deployment.deployment_engine.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        def capture_add(obj):
            obj.id = "dep-new"
            obj.venture_id = "ven-1"
            obj.name = data.name
            obj.target = data.target
            obj.status = "pending"
            obj.config = data.config
            obj.version = 1
            obj.url = None
            obj.health_check_url = None
            obj.deployed_at = None
            obj.created_at = datetime(2024, 6, 1, tzinfo=UTC)

        mock_session.add.side_effect = capture_add

        result = await engine.create_deployment("ven-1", data)

    assert result.name == "my-app"
    assert result.target == "fly"
    assert result.status == "pending"
    assert result.version == 1
    mock_event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_deploy_updates_status(mock_session, mock_event_bus):
    """Test that deploy updates status to active and increments version."""
    engine = DeploymentEngine()

    dep = _make_deployment(version=1, status="pending")
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = dep
    mock_session.execute.return_value = mock_result

    with (
        patch("ai_flywheel.modules.deployment.deployment_engine.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.deployment.deployment_engine.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        request = DeployRequest(deployment_id="dep-1")
        result = await engine.deploy("ven-1", request)

    assert result.status == "active"
    assert result.version == 2
    assert result.url is not None
    assert "dep-1" in result.deployment_id
    assert "building" in result.events
    assert "deployed" in result.events
    assert "health_check_passed" in result.events


@pytest.mark.asyncio
async def test_rollback(mock_session, mock_event_bus):
    """Test rollback decrements version and updates status."""
    engine = DeploymentEngine()

    dep = _make_deployment(version=3, status="active")
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = dep
    mock_session.execute.return_value = mock_result

    with (
        patch("ai_flywheel.modules.deployment.deployment_engine.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.deployment.deployment_engine.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        request = RollbackRequest(deployment_id="dep-1")
        result = await engine.rollback("ven-1", request)

    assert result.rolled_back_to_version == 2
    assert result.status == "rolled_back"
    mock_event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_health_check(mock_session):
    """Test health check returns healthy (simulated)."""
    engine = DeploymentEngine()

    dep = _make_deployment(status="active")
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = dep
    mock_session.execute.return_value = mock_result

    with patch("ai_flywheel.modules.deployment.deployment_engine.service.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await engine.health_check("ven-1", "dep-1")

    assert result.healthy is True
    assert result.status_code == 200
    assert result.latency_ms == 45.0
    assert result.checked_at is not None


@pytest.mark.asyncio
async def test_get_events(mock_session):
    """Test getting deployment events."""
    engine = DeploymentEngine()

    events = [_make_event("evt-1", "created"), _make_event("evt-2", "deployed")]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = events
    mock_session.execute.return_value = mock_result

    with patch("ai_flywheel.modules.deployment.deployment_engine.service.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await engine.get_events("ven-1", "dep-1")

    assert len(result) == 2
    assert result[0]["event_type"] == "created"
    assert result[1]["event_type"] == "deployed"
