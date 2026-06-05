"""Unit tests for ABTestEngine service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.experimentation.ab_testing.schemas import (
    ExperimentCreate,
    RecordObservationRequest,
)
from ai_flywheel.modules.experimentation.ab_testing.service import (
    ABTestEngine,
    _z_test_conversion,
)


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
def fake_experiment():
    """Create a fake Experiment ORM object."""
    exp = MagicMock()
    exp.id = "exp-001"
    exp.venture_id = "ven-001"
    exp.name = "Button Color Test"
    exp.hypothesis = "Red button converts better than blue"
    exp.status = "running"
    exp.experiment_type = "ab_test"
    exp.variants = [
        {"name": "control", "is_control": True, "description": "Blue button"},
        {"name": "treatment", "is_control": False, "description": "Red button"},
    ]
    exp.metric_name = "click_through_rate"
    exp.metric_type = "conversion"
    exp.traffic_split = {"control": 50.0, "treatment": 50.0}
    exp.sample_size_target = 1000
    exp.current_sample_size = 0
    exp.confidence_level = 0.95
    exp.winner = None
    exp.started_at = datetime(2024, 1, 1, tzinfo=UTC)
    exp.completed_at = None
    exp.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    exp.deleted_at = None
    return exp


@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_session")
async def test_create_experiment(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer,
):
    """create_experiment should persist experiment and emit event."""
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
                obj.id = "exp-001"
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)
            if hasattr(obj, "started_at"):
                obj.started_at = None
            if hasattr(obj, "completed_at"):
                obj.completed_at = None
            if hasattr(obj, "winner"):
                obj.winner = None

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    engine = ABTestEngine()
    data = ExperimentCreate(
        name="Button Color Test",
        hypothesis="Red button converts better",
        variants=[
            {"name": "control", "is_control": True},
            {"name": "treatment", "is_control": False},
        ],
        metric_name="click_through_rate",
        metric_type="conversion",
    )
    result = await engine.create_experiment("ven-001", data)

    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "experiment.created"
    assert publish_kwargs["venture_id"] == "ven-001"


@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_session")
async def test_assign_variant_consistent(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_experiment,
):
    """assign_variant should return the same variant for the same user (deterministic)."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_experiment
    mock_session.execute.return_value = mock_result

    engine = ABTestEngine()

    # Same user should get same variant every time
    variant1 = await engine.assign_variant("ven-001", "exp-001", "user_123")
    variant2 = await engine.assign_variant("ven-001", "exp-001", "user_123")
    assert variant1 == variant2
    assert variant1 in ("control", "treatment")

    # Different user may get different variant (but still deterministic)
    variant3 = await engine.assign_variant("ven-001", "exp-001", "user_456")
    assert variant3 in ("control", "treatment")


@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_session")
async def test_record_observation(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_experiment,
):
    """record_observation should persist observation and increment sample size."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_experiment
    mock_session.execute.return_value = mock_result

    engine = ABTestEngine()
    request = RecordObservationRequest(
        experiment_id="exp-001",
        variant_name="treatment",
        value=1.0,
        user_id="user_123",
    )
    await engine.record_observation("ven-001", request)

    mock_session.add.assert_called_once()
    assert fake_experiment.current_sample_size == 1
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "experiment.observation.recorded"


def test_z_test_conversion():
    """Test z-test math with known values.

    Using known proportions:
    - Control: 100 successes out of 1000 (10% conversion)
    - Treatment: 130 successes out of 1000 (13% conversion)
    Expected: significant result (p < 0.05)
    """
    p_value = _z_test_conversion(
        successes1=100, n1=1000,
        successes2=130, n2=1000,
    )
    assert p_value is not None
    # With these proportions the difference is significant
    assert p_value < 0.05

    # Equal proportions should NOT be significant
    p_value_equal = _z_test_conversion(
        successes1=100, n1=1000,
        successes2=100, n2=1000,
    )
    assert p_value_equal is not None
    # p-value should be 1.0 (or very close) for identical proportions
    assert p_value_equal > 0.99

    # Edge case: empty samples should return None
    assert _z_test_conversion(0, 0, 0, 0) is None


@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_session")
async def test_get_results_finds_winner(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_experiment,
):
    """get_results should detect a winner when there's a significant difference."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Create mock observations: control 10% conv, treatment 15% conv
    observations = []
    # Control: 100 successes, 900 failures = 10% conversion
    for i in range(100):
        obs = MagicMock()
        obs.variant_name = "control"
        obs.value = 1.0
        obs.deleted_at = None
        observations.append(obs)
    for i in range(900):
        obs = MagicMock()
        obs.variant_name = "control"
        obs.value = 0.0
        obs.deleted_at = None
        observations.append(obs)
    # Treatment: 150 successes, 850 failures = 15% conversion
    for i in range(150):
        obs = MagicMock()
        obs.variant_name = "treatment"
        obs.value = 1.0
        obs.deleted_at = None
        observations.append(obs)
    for i in range(850):
        obs = MagicMock()
        obs.variant_name = "treatment"
        obs.value = 0.0
        obs.deleted_at = None
        observations.append(obs)

    # Mock session to return experiment then observations
    call_count = [0]

    def execute_side_effect(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # First call: get experiment
            result.scalar_one.return_value = fake_experiment
        else:
            # Second call: get observations
            result.scalars.return_value.all.return_value = observations
        return result

    mock_session.execute = AsyncMock(side_effect=execute_side_effect)

    engine = ABTestEngine()
    results = await engine.get_results("ven-001", "exp-001")

    assert results.is_significant is True
    assert results.winner == "treatment"
    assert results.p_value is not None
    assert results.p_value < 0.05


@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_tracer")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_event_bus")
@patch("ai_flywheel.modules.experimentation.ab_testing.service.get_session")
async def test_conclude_experiment(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_experiment,
):
    """conclude_experiment should compute results, mark completed, and emit event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Simple observations with no clear winner (equal proportions)
    observations = []
    for i in range(50):
        obs = MagicMock()
        obs.variant_name = "control"
        obs.value = 1.0
        obs.deleted_at = None
        observations.append(obs)
    for i in range(50):
        obs = MagicMock()
        obs.variant_name = "treatment"
        obs.value = 1.0
        obs.deleted_at = None
        observations.append(obs)

    call_count = [0]

    def execute_side_effect(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] <= 2:
            # get_results: experiment + observations, then conclude: experiment
            result.scalar_one.return_value = fake_experiment
            result.scalars.return_value.all.return_value = observations
        else:
            result.scalar_one.return_value = fake_experiment
        return result

    mock_session.execute = AsyncMock(side_effect=execute_side_effect)

    engine = ABTestEngine()
    results = await engine.conclude_experiment("ven-001", "exp-001")

    # Should mark as completed
    assert fake_experiment.status == "completed"
    # Event should be emitted
    event_calls = [
        c for c in mock_event_bus.publish.call_args_list
        if c[1].get("event_type") == "experiment.completed"
    ]
    assert len(event_calls) == 1
