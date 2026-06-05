# ruff: noqa: E501
"""Unit tests for the Simulation Engine service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.ml_evaluation.simulation.schemas import (
    RunSimulationRequest,
    SimulationCreate,
)
from ai_flywheel.modules.ml_evaluation.simulation.service import (
    COST_PER_SCENARIO,
    SimulationEngine,
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


def _make_simulation(
    id_="sim-1",
    name="Test Simulation",
    scenarios=None,
    status="draft",
):
    """Create a mock Simulation ORM object."""
    sim = MagicMock()
    sim.id = id_
    sim.venture_id = "ven-1"
    sim.name = name
    sim.description = "A test simulation"
    sim.workflow_blueprint_id = None
    sim.scenarios = scenarios or []
    sim.status = status
    sim.results = None
    sim.total_scenarios = len(scenarios or [])
    sim.passed_scenarios = 0
    sim.failed_scenarios = 0
    sim.duration_ms = None
    sim.cost_estimate_usd = None
    sim.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    sim.deleted_at = None
    return sim


@pytest.mark.asyncio
async def test_create_simulation(mock_session, mock_event_bus):
    """Test creating a simulation."""
    engine = SimulationEngine()

    data = SimulationCreate(
        name="Load Test",
        description="Test under load",
        scenarios=[{"name": "scenario1", "input_data": {"key": "value"}}],
    )

    _make_simulation(scenarios=data.scenarios)
    mock_session.refresh.side_effect = lambda obj: None

    with (
        patch("ai_flywheel.modules.ml_evaluation.simulation.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.ml_evaluation.simulation.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        # Patch the session.add to capture the simulation
        captured = {}

        def capture_add(obj):
            captured["sim"] = obj
            # Copy attributes from our mock
            obj.id = "sim-new"
            obj.venture_id = "ven-1"
            obj.name = data.name
            obj.description = data.description
            obj.workflow_blueprint_id = None
            obj.scenarios = data.scenarios
            obj.status = "draft"
            obj.total_scenarios = 1
            obj.passed_scenarios = 0
            obj.failed_scenarios = 0
            obj.duration_ms = None
            obj.cost_estimate_usd = None
            obj.created_at = datetime(2024, 6, 1, tzinfo=UTC)
            obj.deleted_at = None

        mock_session.add.side_effect = capture_add

        result = await engine.create_simulation("ven-1", data)

    assert result.name == "Load Test"
    assert result.status == "draft"
    assert result.scenarios_count == 1
    mock_event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_run_passes_matching_scenarios(mock_session, mock_event_bus):
    """Test that scenarios with matching input/expected pass."""
    engine = SimulationEngine()

    scenarios = [
        {"name": "match1", "input_data": {"status": "ok", "code": 200}, "expected_outcome": {"status": "ok"}},
        {"name": "match2", "input_data": {"active": True}, "expected_outcome": {"active": True}},
    ]
    sim = _make_simulation(scenarios=scenarios)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = sim
    mock_session.execute.return_value = mock_result

    with (
        patch("ai_flywheel.modules.ml_evaluation.simulation.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.ml_evaluation.simulation.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        request = RunSimulationRequest(simulation_id="sim-1")
        result = await engine.run("ven-1", request)

    assert result.status == "completed"
    assert result.total_scenarios == 2
    assert result.passed_scenarios == 2
    assert result.failed_scenarios == 0


@pytest.mark.asyncio
async def test_run_fails_on_mismatch(mock_session, mock_event_bus):
    """Test that scenarios with mismatched input/expected fail, and failure injection always fails."""
    engine = SimulationEngine()

    scenarios = [
        {"name": "mismatch", "input_data": {"status": "error"}, "expected_outcome": {"status": "ok"}},
        {"name": "injected", "input_data": {"x": 1}, "failure_injection": {"type": "timeout"}},
    ]
    sim = _make_simulation(scenarios=scenarios)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = sim
    mock_session.execute.return_value = mock_result

    with (
        patch("ai_flywheel.modules.ml_evaluation.simulation.service.get_session") as mock_get_session,
        patch("ai_flywheel.modules.ml_evaluation.simulation.service.get_event_bus") as mock_get_bus,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_bus.return_value = mock_event_bus

        request = RunSimulationRequest(simulation_id="sim-1")
        result = await engine.run("ven-1", request)

    assert result.status == "completed"
    assert result.total_scenarios == 2
    assert result.passed_scenarios == 0
    assert result.failed_scenarios == 2


@pytest.mark.asyncio
async def test_estimate_cost(mock_session):
    """Test cost estimation is $0.01 per scenario."""
    engine = SimulationEngine()

    scenarios = [{"name": f"s{i}", "input_data": {}} for i in range(10)]
    sim = _make_simulation(scenarios=scenarios)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = sim
    mock_session.execute.return_value = mock_result

    with patch("ai_flywheel.modules.ml_evaluation.simulation.service.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

        cost = await engine.estimate_cost("ven-1", "sim-1")

    assert cost == 10 * COST_PER_SCENARIO
    assert cost == 0.10
