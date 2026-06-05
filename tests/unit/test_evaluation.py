# ruff: noqa: E501
"""Unit tests for the Evaluation Framework service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.ml_evaluation.evaluation.schemas import (
    EvalSuiteCreate,
    RunEvalRequest,
)
from ai_flywheel.modules.ml_evaluation.evaluation.service import (
    EvaluationFramework,
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


@pytest.fixture
def mock_tracer():
    """Mock tracer with span async context manager."""
    tracer = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=MagicMock())
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm
    return tracer


def _make_eval_suite(
    id_="suite-1",
    name="Accuracy Suite",
    metrics=None,
    test_cases=None,
):
    """Create a mock EvalSuite ORM object."""
    suite = MagicMock()
    suite.id = id_
    suite.venture_id = "ven-1"
    suite.name = name
    suite.description = "A test suite"
    suite.target_module = "agent_factory"
    suite.metrics = metrics or [
        {"name": "accuracy", "metric_type": "exact_match", "weight": 1.0, "threshold": 0.5}
    ]
    suite.test_cases = test_cases or []
    suite.status = "active"
    suite.last_run_at = None
    suite.last_score = None
    suite.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    suite.deleted_at = None
    return suite


def _make_eval_run(id_="run-1", suite_id="suite-1"):
    """Create a mock EvalRun ORM object."""
    run = MagicMock()
    run.id = id_
    run.suite_id = suite_id
    run.venture_id = "ven-1"
    run.status = "completed"
    run.scores = {"overall": 0.8, "per_metric": {"accuracy": 0.8}}
    run.total_cases = 2
    run.passed_cases = 1
    run.failed_cases = 1
    run.duration_ms = 50.0
    run.config = {}
    run.run_at = datetime(2024, 6, 1, tzinfo=UTC)
    run.deleted_at = None
    return run


@pytest.mark.asyncio
@patch("ai_flywheel.modules.ml_evaluation.evaluation.service.get_event_bus")
@patch("ai_flywheel.modules.ml_evaluation.evaluation.service.get_session")
async def test_create_suite(mock_get_session, mock_get_event_bus, mock_session, mock_event_bus):
    """Test creating a new evaluation suite."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    mock_session.refresh = AsyncMock(side_effect=lambda s: None)

    # Capture the added object
    def capture_add(obj):
        obj.id = "suite-new"
        obj.venture_id = "ven-1"
        obj.name = "My Suite"
        obj.description = "test"
        obj.target_module = "agent_factory"
        obj.metrics = [{"name": "accuracy", "metric_type": "exact_match", "weight": 1.0, "threshold": 0.5}]
        obj.test_cases = []
        obj.status = "active"
        obj.last_run_at = None
        obj.last_score = None
        obj.created_at = datetime(2024, 6, 1, tzinfo=UTC)

    mock_session.add = MagicMock(side_effect=capture_add)

    engine = EvaluationFramework()
    data = EvalSuiteCreate(
        name="My Suite",
        description="test",
        target_module="agent_factory",
        metrics=[{"name": "accuracy", "metric_type": "exact_match", "weight": 1.0, "threshold": 0.5}],
    )

    result = await engine.create_suite("ven-1", data)

    assert result.name == "My Suite"
    assert result.status == "active"
    mock_event_bus.publish.assert_awaited()


def test_exact_match_scoring():
    """Test exact_match scoring: 1.0 for match, 0.0 for mismatch."""
    fw = EvaluationFramework()

    # Exact match
    score = fw._score_metric("exact_match", {"answer": "yes"}, {"answer": "yes"})
    assert score == 1.0

    # No match
    score = fw._score_metric("exact_match", {"answer": "no"}, {"answer": "yes"})
    assert score == 0.0


def test_contains_scoring():
    """Test contains scoring: 1.0 when expected is contained in output."""
    fw = EvaluationFramework()

    # Output contains expected
    output = {"text": "The answer is 42"}
    expected = {"text": "The answer is 42"}
    score = fw._score_metric("contains", output, expected)
    assert score == 1.0

    # Output does NOT contain expected
    output = {"text": "Something else"}
    expected = {"text": "The answer is 42"}
    score = fw._score_metric("contains", output, expected)
    assert score == 0.0


def test_numeric_closeness_scoring():
    """Test numeric_closeness scoring based on proximity."""
    fw = EvaluationFramework()

    # Exact numeric match
    score = fw._score_metric("numeric_closeness", {"value": 100}, {"value": 100})
    assert score == 1.0

    # Close values
    score = fw._score_metric("numeric_closeness", {"value": 95}, {"value": 100})
    assert score == pytest.approx(0.95, abs=0.01)

    # Far values — score should be lower
    score = fw._score_metric("numeric_closeness", {"value": 50}, {"value": 100})
    assert score == pytest.approx(0.5, abs=0.01)


@pytest.mark.asyncio
@patch("ai_flywheel.modules.ml_evaluation.evaluation.service.get_event_bus")
@patch("ai_flywheel.modules.ml_evaluation.evaluation.service.get_tracer")
@patch("ai_flywheel.modules.ml_evaluation.evaluation.service.get_session")
async def test_run_evaluation_aggregates(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test running an evaluation aggregates scores correctly."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Suite with 2 test cases: one matching, one not
    suite = _make_eval_suite(
        metrics=[{"name": "accuracy", "metric_type": "exact_match", "weight": 1.0, "threshold": 0.5}],
        test_cases=[
            {"input": {"answer": "yes"}, "expected_output": {"answer": "yes"}},
            {"input": {"answer": "no"}, "expected_output": {"answer": "yes"}},
        ],
    )

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = suite
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock run object to get an id
    def capture_add(obj):
        obj.id = "run-new"

    mock_session.add = MagicMock(side_effect=capture_add)
    mock_session.refresh = AsyncMock(side_effect=lambda obj: None)

    engine = EvaluationFramework()
    request = RunEvalRequest(suite_id="suite-1")

    result = await engine.run_evaluation("ven-1", request)

    assert result.total_cases == 2
    # First case exact match = 1.0, second = 0.0 → overall = 0.5
    assert result.overall_score == pytest.approx(0.5, abs=0.01)
    assert result.passed_cases == 1
    assert result.failed_cases == 1
    mock_event_bus.publish.assert_awaited()
