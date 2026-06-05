# ruff: noqa: E501
"""Unit tests for the Model Forge service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.ml_evaluation.model_forge.schemas import (
    ModelCreate,
    ModelResponse,
    PredictRequest,
    TrainingRunResponse,
    TrainRequest,
)
from ai_flywheel.modules.ml_evaluation.model_forge.service import ModelForge


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


def _make_model_definition(
    id_="model-1",
    name="Test Classifier",
    model_type="classifier",
    status="draft",
    version=1,
):
    """Create a mock ModelDefinition ORM object."""
    model = MagicMock()
    model.id = id_
    model.venture_id = "ven-1"
    model.name = name
    model.description = "A test model"
    model.model_type = model_type
    model.framework = "sklearn"
    model.algorithm = "logistic_regression"
    model.hyperparameters = {}
    model.feature_set_id = None
    model.status = status
    model.version = version
    model.metrics = None
    model.training_duration_ms = None
    model.training_samples = None
    model.artifact_path = None
    model.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    model.deleted_at = None
    return model


def _make_training_run(
    id_="run-1",
    model_id="model-1",
    status="completed",
):
    """Create a mock TrainingRun ORM object."""
    run = MagicMock()
    run.id = id_
    run.model_id = model_id
    run.venture_id = "ven-1"
    run.status = status
    run.hyperparameters = {}
    run.metrics = {"accuracy": 0.75}
    run.training_samples = 80
    run.validation_samples = 20
    run.duration_ms = 100.0
    run.started_at = datetime(2024, 6, 1, tzinfo=UTC)
    run.completed_at = datetime(2024, 6, 1, tzinfo=UTC)
    run.error_message = None
    return run


@pytest.mark.asyncio
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_event_bus")
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_tracer")
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_session")
async def test_create_model(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test creating a new model definition."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    with patch(
        "ai_flywheel.modules.ml_evaluation.model_forge.schemas.ModelResponse.model_validate"
    ) as mock_validate:
        mock_validate.return_value = ModelResponse(
            id="model-new",
            venture_id="ven-1",
            name="Sentiment Classifier",
            description="Classify sentiment",
            model_type="classifier",
            framework="sklearn",
            algorithm="logistic_regression",
            hyperparameters={},
            feature_set_id=None,
            status="draft",
            version=1,
            metrics=None,
            training_duration_ms=None,
            training_samples=None,
            created_at=datetime(2024, 6, 1, tzinfo=UTC),
        )

        engine = ModelForge()
        data = ModelCreate(
            name="Sentiment Classifier",
            description="Classify sentiment",
            model_type="classifier",
        )

        result = await engine.create_model("ven-1", data)

    assert result.id == "model-new"
    assert result.status == "draft"
    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited()


@pytest.mark.asyncio
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_event_bus")
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_tracer")
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_session")
async def test_train_records_run(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that training a model records a training run with metrics."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Mock the training run insertion
    run_mock = MagicMock()
    run_mock.id = "run-1"

    def capture_add(obj):
        obj.id = "run-1"

    mock_session.add = MagicMock(side_effect=capture_add)

    # Mock the model select for updating
    model_def = _make_model_definition()
    mock_model_result = MagicMock()
    mock_model_result.scalar_one.return_value = model_def
    mock_session.execute = AsyncMock(return_value=mock_model_result)

    engine = ModelForge()
    request = TrainRequest(
        model_id="model-1",
        training_data=[{"x": i} for i in range(100)],
        labels=["pos"] * 70 + ["neg"] * 30,
        validation_split=0.2,
    )

    result = await engine.train("ven-1", request)

    assert result.status == "completed"
    assert result.run_id == "run-1"
    assert result.training_samples == 80
    assert result.validation_samples == 20
    assert "accuracy" in result.metrics


@pytest.mark.asyncio
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_event_bus")
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_tracer")
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_session")
async def test_predict_returns_results(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that predict returns predictions using majority class baseline."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Mock get_model
    model_def = _make_model_definition(status="trained", version=2)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = model_def
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = ModelForge()
    # Simulate trained state with majority class "pos"
    engine._trained_models["model-1"] = {
        "train_labels": ["pos"] * 70 + ["neg"] * 30,
        "label_distribution": {"pos": 70, "neg": 30},
        "hyperparameters": {},
        "algorithm": "baseline",
    }

    request = PredictRequest(
        model_id="model-1",
        records=[{"text": "sample 1"}, {"text": "sample 2"}],
    )

    result = await engine.predict("ven-1", request)

    assert len(result.predictions) == 2
    # Majority class baseline should predict "pos" for all
    assert all(p == "pos" for p in result.predictions)
    assert result.probabilities is not None
    assert len(result.probabilities) == 2


@pytest.mark.asyncio
@patch("ai_flywheel.modules.ml_evaluation.model_forge.service.get_session")
async def test_get_training_history(mock_get_session, mock_session):
    """Test retrieving training history for a model."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

    run = _make_training_run()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [run]
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "ai_flywheel.modules.ml_evaluation.model_forge.schemas.TrainingRunResponse.model_validate"
    ) as mock_validate:
        mock_validate.return_value = TrainingRunResponse(
            id="run-1",
            model_id="model-1",
            status="completed",
            hyperparameters={},
            metrics={"accuracy": 0.75},
            training_samples=80,
            validation_samples=20,
            duration_ms=100.0,
            started_at=datetime(2024, 6, 1, tzinfo=UTC),
            completed_at=datetime(2024, 6, 1, tzinfo=UTC),
        )

        engine = ModelForge()
        history = await engine.get_training_history("ven-1", "model-1")

    assert len(history) == 1
    assert history[0].status == "completed"
    assert history[0].metrics == {"accuracy": 0.75}
