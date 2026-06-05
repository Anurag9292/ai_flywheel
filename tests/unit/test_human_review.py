# ruff: noqa: E501
"""Unit tests for the Human Review Engine service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.agent_runtime.human_review.schemas import (
    ReviewDecision,
    ReviewRequest,
    ReviewResponse,
)
from ai_flywheel.modules.agent_runtime.human_review.service import HumanReviewEngine


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
    """Mock tracer with span async context manager."""
    tracer = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=MagicMock())
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm
    return tracer


def _make_review_item(
    id_="review-1",
    venture_id="ven-1",
    item_type="agent_output",
    status="pending",
    priority="medium",
    source_workflow_id=None,
):
    """Create a mock ReviewItem ORM object."""
    item = MagicMock()
    item.id = id_
    item.venture_id = venture_id
    item.item_type = item_type
    item.status = status
    item.priority = priority
    item.content = {"text": "some output"}
    item.context = {}
    item.source_agent_id = "agent-1"
    item.source_workflow_id = source_workflow_id
    item.assigned_to = None
    item.decision = None
    item.reviewer_notes = None
    item.edited_content = None
    item.confidence_score = 0.6
    item.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    item.reviewed_at = None
    item.expires_at = None
    return item


def _make_review_policy(
    id_="pol-1",
    venture_id="ven-1",
    trigger_condition=None,
    routing=None,
):
    """Create a mock ReviewPolicy ORM object."""
    policy = MagicMock()
    policy.id = id_
    policy.venture_id = venture_id
    policy.name = "Test Policy"
    policy.trigger_condition = trigger_condition or {"always": True}
    policy.routing = routing or {"assign_to": "reviewer-1"}
    policy.is_active = True
    policy.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    return policy


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_session")
async def test_submit_for_review(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test submitting an item for human review."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Mock policy lookup (no policies)
    mock_policy_result = MagicMock()
    mock_policy_result.scalars.return_value.all.return_value = []

    # First call: _resolve_routing policy lookup, second call: inside submit
    def mock_execute_side_effect(*args, **kwargs):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)

    # Mock model_validate on flush
    with patch(
        "ai_flywheel.modules.agent_runtime.human_review.schemas.ReviewResponse.model_validate"
    ) as mock_validate:
        mock_validate.return_value = ReviewResponse(
            id="review-1",
            venture_id="ven-1",
            item_type="agent_output",
            status="pending",
            priority="medium",
            content={"text": "output"},
            context={},
            source_agent_id="agent-1",
            assigned_to=None,
            decision=None,
            reviewer_notes=None,
            edited_content=None,
            confidence_score=0.6,
            created_at=datetime(2024, 6, 1, tzinfo=UTC),
            reviewed_at=None,
            expires_at=None,
        )

        engine = HumanReviewEngine()
        request = ReviewRequest(
            item_type="agent_output",
            content={"text": "output"},
            source_agent_id="agent-1",
            priority="medium",
            confidence_score=0.6,
        )

        result = await engine.submit_for_review("ven-1", request)

    assert result.id == "review-1"
    assert result.status == "pending"
    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited()


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.human_review.service.signal_workflow")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_session")
async def test_decide_approved(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_signal_workflow, mock_session, mock_tracer, mock_event_bus):
    """Test recording an approval decision on a review item without workflow."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    item = _make_review_item(source_workflow_id=None)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = item
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "ai_flywheel.modules.agent_runtime.human_review.schemas.ReviewResponse.model_validate"
    ) as mock_validate:
        mock_validate.return_value = ReviewResponse(
            id="review-1",
            venture_id="ven-1",
            item_type="agent_output",
            status="approved",
            priority="medium",
            content={"text": "output"},
            context={},
            source_agent_id="agent-1",
            assigned_to=None,
            decision="approve",
            reviewer_notes="Looks good",
            edited_content=None,
            confidence_score=0.6,
            created_at=datetime(2024, 6, 1, tzinfo=UTC),
            reviewed_at=datetime(2024, 6, 2, tzinfo=UTC),
            expires_at=None,
        )

        engine = HumanReviewEngine()
        decision = ReviewDecision(
            review_id="review-1",
            decision="approve",
            notes="Looks good",
        )

        result = await engine.decide("ven-1", decision)

    assert result.status == "approved"
    assert result.decision == "approve"
    # No workflow signal since source_workflow_id is None
    mock_signal_workflow.assert_not_awaited()


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.human_review.service.signal_workflow")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_session")
async def test_decide_signals_workflow(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_signal_workflow, mock_session, mock_tracer, mock_event_bus):
    """Test that deciding on a review item signals the waiting workflow."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus
    mock_signal_workflow.return_value = None

    item = _make_review_item(source_workflow_id="workflow-123")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = item
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "ai_flywheel.modules.agent_runtime.human_review.schemas.ReviewResponse.model_validate"
    ) as mock_validate:
        mock_validate.return_value = ReviewResponse(
            id="review-1",
            venture_id="ven-1",
            item_type="agent_output",
            status="approved",
            priority="medium",
            content={"text": "output"},
            context={},
            source_agent_id="agent-1",
            assigned_to=None,
            decision="approve",
            reviewer_notes=None,
            edited_content=None,
            confidence_score=0.6,
            created_at=datetime(2024, 6, 1, tzinfo=UTC),
            reviewed_at=datetime(2024, 6, 2, tzinfo=UTC),
            expires_at=None,
        )

        engine = HumanReviewEngine()
        decision = ReviewDecision(review_id="review-1", decision="approve")

        await engine.decide("ven-1", decision)

    mock_signal_workflow.assert_awaited_once_with(
        "workflow-123",
        "review_completed",
        {"decision": "approve", "review_id": "review-1", "notes": ""},
    )


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_session")
async def test_check_needs_review_with_policy(mock_get_session, mock_get_tracer, mock_session, mock_tracer):
    """Test that check_needs_review returns True when a matching policy exists."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer

    # Policy with confidence_below trigger
    policy = _make_review_policy(
        trigger_condition={"confidence_below": 0.8}
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [policy]
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = HumanReviewEngine()

    # Confidence 0.5 < 0.8 → needs review
    needs_review = await engine.check_needs_review(
        "ven-1", "agent_output", confidence=0.5
    )
    assert needs_review is True


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.human_review.service.get_session")
async def test_escalate_overdue(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that overdue pending items get their priority escalated."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Item created 48 hours ago with "low" priority
    old_item = _make_review_item(priority="low")
    old_item.created_at = datetime.now(UTC) - timedelta(hours=48)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [old_item]
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = HumanReviewEngine()
    escalated = await engine.escalate_overdue("ven-1", hours_overdue=24)

    assert escalated == 1
    assert old_item.priority == "medium"
    mock_event_bus.publish.assert_awaited()
