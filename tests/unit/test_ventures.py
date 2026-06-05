"""Unit tests for VentureService and VentureContext."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.ventures.context import (
    get_current_venture_id,
    require_venture_id,
    venture_context,
)
from ai_flywheel.ventures.service import VentureService


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_event_bus():
    """Mock the event bus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def fake_venture():
    """Create a fake Venture ORM object."""
    venture = MagicMock()
    venture.id = "ven-test-001"
    venture.name = "Test Venture"
    venture.domain = "AI/ML"
    venture.status = "active"
    venture.config = {"key": "value"}
    venture.is_deleted = False
    venture.deleted_at = None
    venture.created_at = None
    venture.updated_at = None
    return venture


@patch("ai_flywheel.ventures.service.get_event_bus")
@patch("ai_flywheel.ventures.service.get_global_session")
async def test_create_venture(mock_get_session, mock_get_event_bus, mock_session, mock_event_bus):
    """create_venture should persist a venture and emit venture.created event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    # Make flush set id and status on the added object (simulating DB defaults)
    def side_effect_flush():
        call_args = mock_session.add.call_args
        obj = call_args[0][0]
        if not obj.id:
            obj.id = "ven-generated-id"
        if not obj.status:
            obj.status = "active"

    mock_session.flush.side_effect = side_effect_flush

    service = VentureService()
    result = await service.create_venture(name="My Venture", domain="Fintech", config={"a": 1})

    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()
    mock_event_bus.publish.assert_awaited_once()

    # Check event type
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "venture.created"
    assert publish_kwargs["payload"]["name"] == "My Venture"


@patch("ai_flywheel.ventures.service.get_global_session")
async def test_get_venture_returns_correct_data(mock_get_session, mock_session, fake_venture):
    """get_venture should return VentureInfo for an existing venture."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_session.get.return_value = fake_venture

    service = VentureService()
    result = await service.get_venture("ven-test-001")

    assert result.id == "ven-test-001"
    assert result.name == "Test Venture"
    assert result.domain == "AI/ML"
    assert result.status == "active"


@patch("ai_flywheel.ventures.service.get_global_session")
async def test_get_venture_raises_for_deleted(mock_get_session, mock_session, fake_venture):
    """get_venture should raise ValueError for a soft-deleted venture."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    fake_venture.is_deleted = True
    mock_session.get.return_value = fake_venture

    service = VentureService()
    with pytest.raises(ValueError, match="Venture not found"):
        await service.get_venture("ven-test-001")


@patch("ai_flywheel.ventures.service.get_global_session")
async def test_list_ventures_filters_by_status(mock_get_session, mock_session):
    """list_ventures with status filter should include filter in query."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

    # Mock execute to return a result set
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    service = VentureService()
    result = await service.list_ventures(status="active")

    assert result == []
    mock_session.execute.assert_awaited_once()


@patch("ai_flywheel.ventures.service.get_event_bus")
@patch("ai_flywheel.ventures.service.get_global_session")
async def test_update_venture_modifies_fields(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_venture
):
    """update_venture should apply changes to allowed fields and emit event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_session.get.return_value = fake_venture

    service = VentureService()
    result = await service.update_venture("ven-test-001", {"name": "Updated Name", "domain": "SaaS"})

    assert fake_venture.name == "Updated Name"
    assert fake_venture.domain == "SaaS"
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "venture.updated"


@patch("ai_flywheel.ventures.service.get_event_bus")
@patch("ai_flywheel.ventures.service.get_global_session")
async def test_archive_venture_soft_deletes(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_venture
):
    """archive_venture should set deleted_at and emit venture.archived event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_session.get.return_value = fake_venture

    service = VentureService()
    await service.archive_venture("ven-test-001")

    assert fake_venture.deleted_at is not None
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "venture.archived"


@patch("ai_flywheel.ventures.context.get_tracer")
async def test_venture_context_sets_and_gets_venture_id(mock_get_tracer):
    """venture_context should set venture_id accessible via get_current_venture_id."""
    mock_tracer = MagicMock()
    mock_get_tracer.return_value = mock_tracer

    async with venture_context("ven-ctx-123") as vid:
        assert vid == "ven-ctx-123"
        assert get_current_venture_id() == "ven-ctx-123"

    # After exiting context, should be reset
    assert get_current_venture_id() is None


def test_require_venture_id_raises_when_not_set():
    """require_venture_id should raise RuntimeError when no context is active."""
    # Ensure we're outside any venture context
    assert get_current_venture_id() is None
    with pytest.raises(RuntimeError, match="No venture context is active"):
        require_venture_id()
