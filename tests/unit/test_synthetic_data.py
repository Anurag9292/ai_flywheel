# ruff: noqa: E501
"""Unit tests for the Synthetic Data Generator service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.ml_evaluation.synthetic_data.schemas import (
    GenerateRequest,
)
from ai_flywheel.modules.ml_evaluation.synthetic_data.service import (
    SyntheticDataGenerator,
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


def _make_dataset(
    id_="ds-1",
    name="Test Dataset",
    record_count=100,
    records=None,
    schema_definition=None,
):
    """Create a mock SyntheticDataset ORM object."""
    ds = MagicMock()
    ds.id = id_
    ds.venture_id = "ven-1"
    ds.name = name
    ds.description = "A test dataset"
    ds.source_dataset_name = None
    ds.generation_method = "statistical"
    ds.record_count = record_count
    ds.schema_definition = schema_definition or {"fields": {"name": {"type": "str"}, "age": {"type": "int"}}}
    ds.quality_score = None
    ds.config = {"records": records or []}
    ds.status = "ready"
    ds.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    ds.deleted_at = None
    return ds


@pytest.mark.asyncio
async def test_generate_statistical(mock_session, mock_event_bus):
    """Test statistical data generation produces correct record count and types."""
    generator = SyntheticDataGenerator()

    request = GenerateRequest(
        name="Users Dataset",
        description="Synthetic users",
        schema_definition={
            "fields": {
                "name": {"type": "str", "length": 8},
                "age": {"type": "int", "min": 18, "max": 65},
                "score": {"type": "float", "mean": 50.0, "std": 10.0},
                "active": {"type": "bool", "true_weight": 0.7},
            }
        },
        record_count=50,
        generation_method="statistical",
    )

    # Test the internal generation logic directly (no DB mocks needed)
    records = generator._generate_records(
        request.schema_definition,
        request.record_count,
        request.generation_method,
        request.seed_records,
    )

    assert len(records) == 50
    for record in records:
        assert isinstance(record["name"], str)
        assert len(record["name"]) == 8
        assert isinstance(record["age"], int)
        assert 18 <= record["age"] <= 65
        assert isinstance(record["score"], float)
        assert isinstance(record["active"], bool)


@pytest.mark.asyncio
async def test_get_dataset(mock_session, mock_event_bus):
    """Test getting a dataset by ID."""
    generator = SyntheticDataGenerator()
    dataset = _make_dataset()

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = dataset
    mock_session.execute.return_value = mock_result

    with patch("ai_flywheel.modules.ml_evaluation.synthetic_data.service.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await generator.get_dataset("ven-1", "ds-1")

    assert result.id == "ds-1"
    assert result.name == "Test Dataset"
    assert result.venture_id == "ven-1"
    assert result.generation_method == "statistical"


@pytest.mark.asyncio
async def test_augment(mock_session, mock_event_bus):
    """Test dataset augmentation multiplies records."""
    generator = SyntheticDataGenerator()

    # Test augmentation logic directly
    existing_records = [
        {"name": "alice", "age": 30},
        {"name": "bob", "age": 25},
    ]
    schema = {"fields": {"name": {"type": "str"}, "age": {"type": "int"}}}

    augmented = generator._augment_records(existing_records, schema, "noise", factor=3)

    # factor=3 means original + 2x new = (3-1) * len(existing) = 4 new records
    assert len(augmented) == 4
    for record in augmented:
        assert "name" in record
        assert "age" in record


@pytest.mark.asyncio
async def test_validate_quality():
    """Test quality validation computes correct score."""
    generator = SyntheticDataGenerator()

    schema = {"fields": {"name": {"type": "str"}, "age": {"type": "int"}, "score": {"type": "float"}}}
    # All records conform to types
    good_records = [
        {"name": "alice", "age": 30, "score": 85.5},
        {"name": "bob", "age": 25, "score": 92.0},
    ]
    score = generator._compute_quality_score(good_records, schema)
    assert score == 1.0

    # Some records have wrong types
    bad_records = [
        {"name": "alice", "age": "thirty", "score": 85.5},  # age is str instead of int
        {"name": 123, "age": 25, "score": "high"},  # name is int, score is str
    ]
    score = generator._compute_quality_score(bad_records, schema)
    assert score < 1.0
    assert score > 0.0  # Some fields still match
