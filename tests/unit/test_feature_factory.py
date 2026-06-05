# ruff: noqa: E501
"""Unit tests for the Feature Factory service and transforms."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.ml_evaluation.feature_factory.schemas import (
    FeatureDefCreate,
    FeatureDefResponse,
)
from ai_flywheel.modules.ml_evaluation.feature_factory.service import FeatureFactory
from ai_flywheel.modules.ml_evaluation.feature_factory.transforms import (
    apply_transform,
    categorical_encode,
    numeric_scale,
    text_length,
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
    """Mock tracer with span async context manager."""
    tracer = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=MagicMock())
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm
    return tracer


@pytest.mark.asyncio
@patch("ai_flywheel.modules.ml_evaluation.feature_factory.service.get_event_bus")
@patch("ai_flywheel.modules.ml_evaluation.feature_factory.service.get_tracer")
@patch("ai_flywheel.modules.ml_evaluation.feature_factory.service.get_session")
async def test_create_feature(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test creating a new feature definition."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    with patch(
        "ai_flywheel.modules.ml_evaluation.feature_factory.schemas.FeatureDefResponse.model_validate"
    ) as mock_validate:
        mock_validate.return_value = FeatureDefResponse(
            id="feat-1",
            venture_id="ven-1",
            name="age_scaled",
            description="Scaled age",
            input_fields=["age"],
            transform_type="numeric",
            transform_config={"mode": "minmax", "min": 0, "max": 100},
            output_dtype="float",
            version=1,
            is_active=True,
            created_at=datetime(2024, 6, 1, tzinfo=UTC),
        )

        engine = FeatureFactory()
        data = FeatureDefCreate(
            name="age_scaled",
            description="Scaled age",
            input_fields=["age"],
            transform_type="numeric",
            transform_config={"mode": "minmax", "min": 0, "max": 100},
        )

        result = await engine.create_feature("ven-1", data)

    assert result.id == "feat-1"
    assert result.name == "age_scaled"
    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited()


def test_numeric_scale_transform():
    """Test numeric_scale with minmax normalization."""
    config = {"mode": "minmax", "min": 0.0, "max": 100.0}

    # 50 should be normalized to 0.5
    assert numeric_scale(50, config) == 0.5
    assert numeric_scale(0, config) == 0.0
    assert numeric_scale(100, config) == 1.0
    # None returns 0.0
    assert numeric_scale(None, config) == 0.0

    # z-score mode
    zscore_config = {"mode": "zscore", "mean": 50.0, "std": 10.0}
    assert numeric_scale(60, zscore_config) == 1.0
    assert numeric_scale(50, zscore_config) == 0.0


def test_categorical_encode():
    """Test categorical label encoding."""
    config = {"mode": "label", "categories": ["red", "green", "blue"]}

    assert categorical_encode("red", config) == 0
    assert categorical_encode("green", config) == 1
    assert categorical_encode("blue", config) == 2
    # Unknown category
    assert categorical_encode("purple", config) == -1

    # One-hot mode
    onehot_config = {"mode": "onehot", "categories": ["red", "green", "blue"]}
    assert categorical_encode("green", onehot_config) == [0, 1, 0]


def test_text_length():
    """Test text_length transform for character and word counting."""
    char_config = {"unit": "char"}
    word_config = {"unit": "word"}

    assert text_length("hello world", char_config) == 11
    assert text_length("hello world", word_config) == 2
    assert text_length(None, char_config) == 0
    assert text_length("", char_config) == 0


def test_compute_applies_all_features():
    """Test that apply_transform dispatches correctly to all feature types."""
    # Numeric feature
    numeric_def = FeatureDefResponse(
        id="f1", venture_id="v1", name="scaled_age",
        description="", input_fields=["age"],
        transform_type="numeric",
        transform_config={"mode": "minmax", "min": 0, "max": 100},
        output_dtype="float", version=1, is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    record = {"age": 25, "category": "blue", "description": "a test sentence"}

    # Numeric
    result = apply_transform(record, numeric_def)
    assert result == 0.25

    # Categorical feature
    cat_def = FeatureDefResponse(
        id="f2", venture_id="v1", name="cat_encoded",
        description="", input_fields=["category"],
        transform_type="categorical",
        transform_config={"mode": "label", "categories": ["red", "green", "blue"]},
        output_dtype="int", version=1, is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    result = apply_transform(record, cat_def)
    assert result == 2  # blue is at index 2

    # Text feature
    text_def = FeatureDefResponse(
        id="f3", venture_id="v1", name="desc_length",
        description="", input_fields=["description"],
        transform_type="text",
        transform_config={"method": "length", "unit": "word"},
        output_dtype="int", version=1, is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    result = apply_transform(record, text_def)
    assert result == 3  # "a test sentence" = 3 words
