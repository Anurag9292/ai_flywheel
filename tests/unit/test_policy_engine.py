# ruff: noqa: E501
"""Unit tests for the Policy Engine service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.agent_runtime.policy_engine.schemas import (
    PolicyCheckRequest,
    PolicyCreate,
    PolicyResponse,
)
from ai_flywheel.modules.agent_runtime.policy_engine.service import PolicyEngine


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


def _make_policy(
    id_="pol-1",
    name="Safety Policy",
    policy_type="keyword_block",
    rules=None,
    enforcement="block",
    scope=None,
):
    """Create a mock Policy ORM object."""
    policy = MagicMock()
    policy.id = id_
    policy.venture_id = "ven-1"
    policy.name = name
    policy.description = "Test policy"
    policy.policy_type = policy_type
    policy.rules = rules or [{"type": "keyword_block", "keywords": ["DROP TABLE"]}]
    policy.enforcement = enforcement
    policy.scope = scope or {"all": True}
    policy.is_active = True
    policy.violation_count = 0
    policy.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    return policy


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_session")
async def test_create_policy(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test creating a new governance policy."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    with patch(
        "ai_flywheel.modules.agent_runtime.policy_engine.schemas.PolicyResponse.model_validate"
    ) as mock_validate:
        mock_validate.return_value = PolicyResponse(
            id="pol-new",
            venture_id="ven-1",
            name="No SQL Injection",
            description="Block SQL injection",
            policy_type="keyword_block",
            rules=[{"type": "keyword_block", "keywords": ["DROP TABLE"]}],
            enforcement="block",
            scope={"all": True},
            is_active=True,
            violation_count=0,
            created_at=datetime(2024, 6, 1, tzinfo=UTC),
        )

        engine = PolicyEngine()
        data = PolicyCreate(
            name="No SQL Injection",
            description="Block SQL injection",
            policy_type="keyword_block",
            rules=[{"type": "keyword_block", "keywords": ["DROP TABLE"]}],
            enforcement="block",
        )

        result = await engine.create_policy("ven-1", data)

    assert result.id == "pol-new"
    assert result.name == "No SQL Injection"
    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited()


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_session")
async def test_check_passes_when_no_violations(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that check passes when action doesn't violate any policies."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Policy with keyword_block for "DROP TABLE"
    policy = _make_policy(
        rules=[{"type": "keyword_block", "keywords": ["DROP TABLE"]}],
        enforcement="block",
    )

    # Mock loading policies
    mock_policy_result = MagicMock()
    mock_policy_result.scalars.return_value.all.return_value = [policy]
    mock_session.execute = AsyncMock(return_value=mock_policy_result)

    engine = PolicyEngine()
    request = PolicyCheckRequest(
        module_name="agent_factory",
        action="SELECT * FROM users",
    )

    result = await engine.check("ven-1", request)

    assert result.allowed is True
    assert len(result.violations) == 0


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_session")
async def test_check_blocks_keyword(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that check blocks when action contains a prohibited keyword."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    policy = _make_policy(
        rules=[{"type": "keyword_block", "keywords": ["DROP TABLE"]}],
        enforcement="block",
    )

    mock_policy_result = MagicMock()
    mock_policy_result.scalars.return_value.all.return_value = [policy]
    mock_session.execute = AsyncMock(return_value=mock_policy_result)

    engine = PolicyEngine()
    request = PolicyCheckRequest(
        module_name="agent_factory",
        action="DROP TABLE users",
    )

    result = await engine.check("ven-1", request)

    assert result.allowed is False
    assert len(result.violations) == 1
    assert "DROP TABLE" in result.violations[0].message


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_session")
async def test_check_blocks_cost_limit(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that check blocks when cost exceeds the configured limit."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    policy = _make_policy(
        rules=[{"type": "cost_limit", "max_usd": 5.0}],
        enforcement="block",
    )

    mock_policy_result = MagicMock()
    mock_policy_result.scalars.return_value.all.return_value = [policy]
    mock_session.execute = AsyncMock(return_value=mock_policy_result)

    engine = PolicyEngine()
    request = PolicyCheckRequest(
        module_name="agent_factory",
        action="execute expensive query",
        context={"cost": 10.0},
    )

    result = await engine.check("ven-1", request)

    assert result.allowed is False
    assert len(result.violations) == 1
    assert "exceeds" in result.violations[0].message.lower()


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.policy_engine.service.get_session")
async def test_records_violation(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that violations are recorded in the database."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    policy = _make_policy(
        rules=[{"type": "keyword_block", "keywords": ["DANGER"]}],
        enforcement="block",
    )

    mock_policy_result = MagicMock()
    mock_policy_result.scalars.return_value.all.return_value = [policy]
    mock_session.execute = AsyncMock(return_value=mock_policy_result)

    engine = PolicyEngine()
    request = PolicyCheckRequest(
        module_name="tool_forge",
        action="DANGER operation",
    )

    result = await engine.check("ven-1", request)

    assert result.allowed is False
    # Verify session.add was called to record the violation
    assert mock_session.add.called
    # Verify the violation event was emitted
    mock_event_bus.publish.assert_awaited()
    call_kwargs = mock_event_bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "policy.violated"
