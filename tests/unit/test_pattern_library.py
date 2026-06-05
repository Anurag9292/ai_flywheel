"""Unit tests for Pattern & Template Library service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.cross_venture.pattern_library.schemas import (
    ApplyPatternRequest,
    PatternCreate,
    PatternSearchRequest,
)
from ai_flywheel.modules.cross_venture.pattern_library.service import PatternLibrary


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def fake_pattern():
    """Create a fake Pattern ORM object."""
    p = MagicMock()
    p.id = "pat-001"
    p.name = "Test Pattern"
    p.description = "A test pattern for agents"
    p.pattern_type = "agent_config"
    p.content = {"system_prompt": "You are helpful"}
    p.tags = ["agent", "test"]
    p.source_venture_id = "ven-001"
    p.success_count = 5
    p.failure_count = 1
    p.confidence_score = 0.833
    p.version = 1
    p.is_active = True
    p.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return p


@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_event_bus")
@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_global_session")
async def test_create_pattern(mock_get_session, mock_get_event_bus, mock_session, mock_event_bus):
    """create_pattern should persist a pattern and emit pattern.created event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    # Simulate flush setting defaults
    def add_side_effect(obj):
        obj.id = "pat-new-001"
        obj.created_at = datetime(2026, 6, 1, tzinfo=UTC)
        obj.success_count = 0
        obj.failure_count = 0
        obj.confidence_score = 0.5
        obj.version = 1
        obj.is_active = True

    mock_session.add.side_effect = add_side_effect

    library = PatternLibrary()
    data = PatternCreate(
        name="New Pattern",
        description="A new agent config pattern",
        pattern_type="agent_config",
        content={"system_prompt": "Be concise"},
        tags=["agent"],
        source_venture_id="ven-001",
    )
    result = await library.create_pattern(data)

    assert result.name == "New Pattern"
    assert result.pattern_type == "agent_config"
    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited_once()
    assert mock_event_bus.publish.call_args[1]["event_type"] == "pattern.created"


@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_global_session")
async def test_search_by_type(mock_get_session, mock_session, fake_pattern):
    """search should filter patterns by type."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

    # First execute returns count, second returns patterns
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    patterns_result = MagicMock()
    patterns_result.scalars.return_value.all.return_value = [fake_pattern]

    mock_session.execute.side_effect = [count_result, patterns_result]

    library = PatternLibrary()
    request = PatternSearchRequest(pattern_type="agent_config")
    result = await library.search(request)

    assert result.total == 1
    assert len(result.patterns) == 1
    assert result.patterns[0].pattern_type == "agent_config"


@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_event_bus")
@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_global_session")
async def test_apply_success_updates_confidence(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_pattern
):
    """apply_pattern with success should increase confidence score."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    # Reset counters for clean test
    fake_pattern.success_count = 3
    fake_pattern.failure_count = 1

    # First execute: get pattern. Second: count applications
    pattern_result = MagicMock()
    pattern_result.scalar_one.return_value = fake_pattern

    count_result = MagicMock()
    count_result.scalar_one.return_value = 5

    mock_session.execute.side_effect = [pattern_result, count_result]

    library = PatternLibrary()
    request = ApplyPatternRequest(
        pattern_id="pat-001", venture_id="ven-002", outcome="success"
    )
    result = await library.apply_pattern(request)

    # success_count goes from 3 to 4, failure stays 1: confidence = 4/5 = 0.8
    assert fake_pattern.success_count == 4
    assert result.new_confidence == pytest.approx(0.8)
    assert result.total_applications == 5


@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_event_bus")
@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_global_session")
async def test_apply_failure_updates_confidence(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_pattern
):
    """apply_pattern with failure should decrease confidence score."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    fake_pattern.success_count = 3
    fake_pattern.failure_count = 1

    pattern_result = MagicMock()
    pattern_result.scalar_one.return_value = fake_pattern

    count_result = MagicMock()
    count_result.scalar_one.return_value = 5

    mock_session.execute.side_effect = [pattern_result, count_result]

    library = PatternLibrary()
    request = ApplyPatternRequest(
        pattern_id="pat-001", venture_id="ven-002", outcome="failure"
    )
    result = await library.apply_pattern(request)

    # failure_count goes from 1 to 2, success stays 3: confidence = 3/5 = 0.6
    assert fake_pattern.failure_count == 2
    assert result.new_confidence == pytest.approx(0.6)


@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_event_bus")
@patch("ai_flywheel.modules.cross_venture.pattern_library.service.get_global_session")
async def test_recommend_for_venture(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_pattern
):
    """recommend_for_venture should return top patterns by confidence."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [fake_pattern]
    mock_session.execute.return_value = result_mock

    library = PatternLibrary()
    results = await library.recommend_for_venture("ven-002", context="Need agent config")

    assert len(results) == 1
    assert results[0].id == "pat-001"
    mock_event_bus.publish.assert_awaited_once()
    assert mock_event_bus.publish.call_args[1]["event_type"] == "pattern.recommended"
