"""Unit tests for CostOptimizer service and listener."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.events import Event
from ai_flywheel.modules.experimentation.cost_optimizer.listener import _handle_cost_event
from ai_flywheel.modules.experimentation.cost_optimizer.schemas import BudgetCreate
from ai_flywheel.modules.experimentation.cost_optimizer.service import CostOptimizer


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
    """Mock tracer."""
    tracer = MagicMock()
    tracer.set_venture_context = MagicMock()
    return tracer


@pytest.fixture
def fake_budget():
    """Create a fake Budget ORM object."""
    budget = MagicMock()
    budget.id = "budget-001"
    budget.venture_id = "ven-001"
    budget.period_type = "monthly"
    budget.limit_usd = 100.0
    budget.alert_threshold_pct = 0.8
    budget.is_active = True
    budget.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    budget.deleted_at = None
    return budget


@pytest.fixture
def fake_alert():
    """Create a fake CostAlert ORM object."""
    alert = MagicMock()
    alert.id = "alert-001"
    alert.venture_id = "ven-001"
    alert.alert_type = "threshold"
    alert.budget_id = "budget-001"
    alert.message = "Approaching budget limit"
    alert.current_spend_usd = 85.0
    alert.limit_usd = 100.0
    alert.period = "2024-01"
    alert.acknowledged = False
    alert.created_at = datetime(2024, 1, 15, tzinfo=UTC)
    return alert


@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_session")
async def test_record_cost_creates_cost_record(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """record_cost should persist a CostRecord and emit cost.recorded event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Mock check_budget to avoid needing budget query setup
    with patch.object(CostOptimizer, "check_budget", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = []

        optimizer = CostOptimizer()
        await optimizer.record_cost(
            venture_id="ven-001",
            module_name="agent_factory",
            operation="llm_call",
            amount_usd=0.03,
            provider="openai",
            model_name="gpt-4o-mini",
            tokens_input=100,
            tokens_output=50,
        )

    mock_session.add.assert_called_once()
    # Verify the added object is a CostRecord
    added_obj = mock_session.add.call_args[0][0]
    assert added_obj.amount_usd == 0.03
    assert added_obj.module_name == "agent_factory"
    assert added_obj.provider == "openai"

    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "cost.recorded"
    assert publish_kwargs["payload"]["amount_usd"] == 0.03


@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_session")
async def test_set_budget_creates_budget(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """set_budget should deactivate existing budgets and create a new one."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Track added objects to simulate DB defaults on flush
    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    mock_session.add.side_effect = add_side_effect

    async def flush_side_effect():
        for obj in added_objects:
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = "budget-generated-001"
            if hasattr(obj, 'created_at') and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    # Mock: no existing budgets, and _get_current_spend returns 0
    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Query for existing budgets
            result.scalars.return_value.all.return_value = []
        else:
            # _get_current_spend query
            result.scalar_one.return_value = 0.0
        return result

    mock_session.execute.side_effect = execute_side_effect

    optimizer = CostOptimizer()
    data = BudgetCreate(
        venture_id="ven-001",
        period_type="monthly",
        limit_usd=100.0,
        alert_threshold_pct=0.8,
    )
    result = await optimizer.set_budget(data)

    mock_session.add.assert_called_once()
    assert result.id == "budget-generated-001"
    assert result.limit_usd == 100.0
    assert result.period_type == "monthly"
    assert result.is_active is True


@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_session")
async def test_check_budget_creates_alert_when_over_threshold(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_budget
):
    """check_budget should create an alert when spend exceeds threshold."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Track added objects and simulate DB defaults on flush
    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    mock_session.add.side_effect = add_side_effect

    async def flush_side_effect():
        for obj in added_objects:
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = "alert-generated-001"
            if hasattr(obj, 'created_at') and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 15, tzinfo=UTC)

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Get active budgets
            result.scalars.return_value.all.return_value = [fake_budget]
        elif call_count[0] == 2:
            # _get_current_spend: returns 85% of limit (over threshold at 80%)
            result.scalar_one.return_value = 85.0
        elif call_count[0] == 3:
            # _create_alert: check for existing alert (none)
            result.scalar_one_or_none.return_value = None
        else:
            result.scalar_one.return_value = None
        return result

    mock_session.execute.side_effect = execute_side_effect

    optimizer = CostOptimizer()
    alerts = await optimizer.check_budget("ven-001")

    # An alert should be created (session.add called)
    assert mock_session.add.called
    # Event should be published for the threshold alert
    mock_event_bus.publish.assert_awaited()
    # Check we got a threshold alert event
    published_events = [
        call[1]["event_type"] for call in mock_event_bus.publish.call_args_list
    ]
    assert "cost.alert.threshold" in published_events


@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.cost_optimizer.service.get_session")
async def test_get_report_aggregates_correctly(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """get_report should return aggregated cost data for the period."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Total spend
            result.scalar_one.return_value = 42.50
        elif call_count[0] == 2:
            # By module
            result.all.return_value = [("agent_factory", 30.0), ("prompt_studio", 12.50)]
        elif call_count[0] == 3:
            # By provider
            result.all.return_value = [("openai", 40.0), ("anthropic", 2.50)]
        elif call_count[0] == 4:
            # By model
            result.all.return_value = [("gpt-4o-mini", 35.0), ("gpt-4o", 7.50)]
        elif call_count[0] == 5:
            # Top operations
            result.all.return_value = [
                ("llm_call", "agent_factory", 30.0, 150),
                ("render", "prompt_studio", 12.50, 50),
            ]
        elif call_count[0] == 6:
            # Budget query
            result.scalar_one_or_none.return_value = None
        return result

    mock_session.execute.side_effect = execute_side_effect

    optimizer = CostOptimizer()
    report = await optimizer.get_report("ven-001", "monthly")

    assert report.venture_id == "ven-001"
    assert report.total_usd == 42.50
    assert report.by_module == {"agent_factory": 30.0, "prompt_studio": 12.50}
    assert report.by_provider == {"openai": 40.0, "anthropic": 2.50}
    assert report.by_model == {"gpt-4o-mini": 35.0, "gpt-4o": 7.50}
    assert len(report.top_operations) == 2


async def test_listener_filters_cost_optimizer_events():
    """The cost listener should skip events from cost_optimizer to avoid loops."""
    event = Event(
        event_type="cost.recorded",
        source_module="cost_optimizer",
        payload={"amount_usd": 0.05},
        venture_id="ven-001",
    )

    # Should not raise or call record_cost
    with patch(
        "ai_flywheel.modules.experimentation.cost_optimizer.listener.CostOptimizer"
    ) as MockOptimizer:
        await _handle_cost_event(event)
        MockOptimizer.assert_not_called()


async def test_listener_skips_events_without_venture_id():
    """The cost listener should skip events without a venture_id."""
    event = Event(
        event_type="agent.execution.completed",
        source_module="agent_factory",
        payload={"cost_usd": 0.05, "provider": "openai"},
        venture_id=None,
    )

    with patch(
        "ai_flywheel.modules.experimentation.cost_optimizer.listener.CostOptimizer"
    ) as MockOptimizer:
        await _handle_cost_event(event)
        MockOptimizer.assert_not_called()


async def test_listener_skips_events_without_cost_data():
    """The cost listener should skip events that have no cost in the payload."""
    event = Event(
        event_type="agent.execution.completed",
        source_module="agent_factory",
        payload={"agent_id": "agent-001", "status": "completed"},
        venture_id="ven-001",
    )

    with patch(
        "ai_flywheel.modules.experimentation.cost_optimizer.listener.CostOptimizer"
    ) as MockOptimizer:
        await _handle_cost_event(event)
        # CostOptimizer() was not instantiated (or record_cost not called)
        if MockOptimizer.called:
            instance = MockOptimizer.return_value
            instance.record_cost.assert_not_awaited()


async def test_listener_processes_valid_cost_event():
    """The cost listener should call record_cost for events with cost data."""
    event = Event(
        event_type="agent.execution.completed",
        source_module="agent_factory",
        payload={
            "cost_usd": 0.05,
            "provider": "openai",
            "model_name": "gpt-4o-mini",
            "tokens_input": 100,
            "tokens_output": 50,
        },
        venture_id="ven-001",
    )

    with patch(
        "ai_flywheel.modules.experimentation.cost_optimizer.listener.CostOptimizer"
    ) as MockOptimizer:
        mock_instance = AsyncMock()
        mock_instance.record_cost = AsyncMock()
        MockOptimizer.return_value = mock_instance

        await _handle_cost_event(event)

        mock_instance.record_cost.assert_awaited_once()
        call_kwargs = mock_instance.record_cost.call_args[1]
        assert call_kwargs["venture_id"] == "ven-001"
        assert call_kwargs["amount_usd"] == 0.05
        assert call_kwargs["provider"] == "openai"
