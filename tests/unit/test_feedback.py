"""Unit tests for FeedbackCollector service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.experimentation.feedback.schemas import (
    FeedbackCreate,
)
from ai_flywheel.modules.experimentation.feedback.service import FeedbackCollector


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
def mock_tracer():
    """Mock tracer with span context manager."""
    tracer = MagicMock()
    tracer.set_venture_context = MagicMock()
    return tracer


@pytest.fixture
def fake_feedback_item():
    """Create a fake FeedbackItem ORM object."""
    item = MagicMock()
    item.id = "fb-001"
    item.venture_id = "ven-001"
    item.feedback_type = "explicit"
    item.category = "rating"
    item.source_module = "prompt_studio"
    item.target_module = "prompt_studio"
    item.entity_id = "output-001"
    item.entity_type = "agent_output"
    item.rating = 4.0
    item.correction_text = None
    item.context = {"session": "s-001"}
    item.quality_score = 0.95
    item.user_id = "user-001"
    item.session_id = "session-001"
    item.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    item.deleted_at = None
    return item


@patch("ai_flywheel.modules.experimentation.feedback.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.feedback.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.feedback.service.get_session")
async def test_collect_feedback_stores_and_routes(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_feedback_item,
):
    """collect should persist feedback, score it, and route via event bus."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    mock_session.add.side_effect = add_side_effect

    async def flush_side_effect():
        for obj in added_objects:
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = "fb-001"
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    collector = FeedbackCollector()
    data = FeedbackCreate(
        feedback_type="explicit",
        category="rating",
        source_module="prompt_studio",
        target_module="prompt_studio",
        entity_id="output-001",
        entity_type="agent_output",
        rating=4.0,
        user_id="user-001",
        session_id="session-001",
        context={"session": "s-001"},
    )
    result = await collector.collect("ven-001", data)

    mock_session.add.assert_called_once()
    # Should publish 2 events: feedback.collected + feedback.received.{target}
    assert mock_event_bus.publish.call_count == 2

    # Check general event
    first_call = mock_event_bus.publish.call_args_list[0][1]
    assert first_call["event_type"] == "feedback.collected"

    # Check routing event
    second_call = mock_event_bus.publish.call_args_list[1][1]
    assert second_call["event_type"] == "feedback.received.prompt_studio"


def test_score_quality_explicit_higher():
    """Explicit feedback should score higher than implicit or automated."""
    collector = FeedbackCollector()

    explicit = FeedbackCreate(
        feedback_type="explicit",
        category="rating",
        source_module="test",
        entity_id="e-1",
        entity_type="agent_output",
    )
    implicit = FeedbackCreate(
        feedback_type="implicit",
        category="click",
        source_module="test",
        entity_id="e-1",
        entity_type="agent_output",
    )
    automated = FeedbackCreate(
        feedback_type="automated",
        category="metric",
        source_module="test",
        entity_id="e-1",
        entity_type="agent_output",
    )

    score_explicit = collector.score_quality(explicit)
    score_implicit = collector.score_quality(implicit)
    score_automated = collector.score_quality(automated)

    assert score_explicit > score_implicit
    assert score_implicit > score_automated


def test_score_quality_with_context_bonus():
    """Feedback with context should score higher than without."""
    collector = FeedbackCollector()

    # Use implicit feedback (base 0.6) so context bonus is visible before cap
    without_context = FeedbackCreate(
        feedback_type="implicit",
        category="click",
        source_module="test",
        entity_id="e-1",
        entity_type="agent_output",
    )
    with_context = FeedbackCreate(
        feedback_type="implicit",
        category="click",
        source_module="test",
        entity_id="e-1",
        entity_type="agent_output",
        context={"step": "generation", "model": "gpt-4", "latency": 1.2},
    )

    score_without = collector.score_quality(without_context)
    score_with = collector.score_quality(with_context)

    assert score_with > score_without


@patch("ai_flywheel.modules.experimentation.feedback.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.feedback.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.feedback.service.get_session")
async def test_get_summary_aggregates(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_feedback_item,
):
    """get_summary should aggregate feedback stats for an entity."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Mock multiple execute calls for different queries
    call_count = [0]

    def execute_side_effect(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Total count
            result.scalar_one.return_value = 10
        elif call_count[0] == 2:
            # Average rating
            result.scalar_one.return_value = 3.8
        elif call_count[0] == 3:
            # Positive count
            result.scalar_one.return_value = 7
        elif call_count[0] == 4:
            # Negative count
            result.scalar_one.return_value = 3
        elif call_count[0] == 5:
            # Correction count
            result.scalar_one.return_value = 2
        else:
            # Recent feedback
            result.scalars.return_value.all.return_value = [fake_feedback_item]
        return result

    mock_session.execute = AsyncMock(side_effect=execute_side_effect)

    collector = FeedbackCollector()
    summary = await collector.get_summary("ven-001", "output-001", "agent_output")

    assert summary.entity_id == "output-001"
    assert summary.entity_type == "agent_output"
    assert summary.total_feedback == 10
    assert summary.avg_rating == 3.8
    assert summary.positive_count == 7
    assert summary.negative_count == 3
    assert summary.correction_count == 2
    assert len(summary.recent_feedback) == 1


@patch("ai_flywheel.modules.experimentation.feedback.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.feedback.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.feedback.service.get_session")
async def test_get_module_feedback_filters(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_feedback_item,
):
    """get_module_feedback should return feedback targeting a specific module."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_feedback_item]
    mock_session.execute.return_value = mock_result

    collector = FeedbackCollector()
    results = await collector.get_module_feedback("ven-001", "prompt_studio", limit=20)

    assert len(results) == 1
    assert results[0].source_module == "prompt_studio"
    mock_session.execute.assert_awaited_once()
