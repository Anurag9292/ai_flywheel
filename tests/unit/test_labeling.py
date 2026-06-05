# ruff: noqa: E501
"""Unit tests for the Labeling & Ground Truth service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.data_knowledge.labeling.schemas import (
    AddItemsRequest,
    LabelRequest,
    TaskCreate,
)
from ai_flywheel.modules.data_knowledge.labeling.service import LabelingEngine


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


def _make_task(id_="task-1", total_items=0, labeled_items=0):
    """Create a mock LabelingTask ORM object."""
    task = MagicMock()
    task.id = id_
    task.venture_id = "ven-1"
    task.name = "Sentiment Task"
    task.description = "Label sentiment"
    task.task_type = "classification"
    task.instructions = "Label as positive or negative"
    task.label_options = ["positive", "negative"]
    task.status = "active"
    task.total_items = total_items
    task.labeled_items = labeled_items
    task.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    task.deleted_at = None
    return task


def _make_label_item(
    id_="item-1",
    task_id="task-1",
    labels=None,
    status="pending",
    consensus_label=None,
):
    """Create a mock LabelItem ORM object."""
    item = MagicMock()
    item.id = id_
    item.venture_id = "ven-1"
    item.task_id = task_id
    item.content = {"text": "Great product!"}
    item.labels = labels or []
    item.consensus_label = consensus_label
    item.is_gold = False
    item.status = status
    item.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    item.deleted_at = None
    return item


@pytest.mark.asyncio
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_event_bus")
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_session")
async def test_create_task(mock_get_session, mock_get_event_bus, mock_session, mock_event_bus):
    """Test creating a labeling task."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    def capture_add(obj):
        obj.id = "task-new"
        obj.venture_id = "ven-1"
        obj.name = "Sentiment Task"
        obj.description = "Label sentiment"
        obj.task_type = "classification"
        obj.instructions = "Label positive or negative"
        obj.label_options = ["positive", "negative"]
        obj.status = "active"
        obj.total_items = 0
        obj.labeled_items = 0
        obj.created_at = datetime(2024, 6, 1, tzinfo=UTC)

    mock_session.add = MagicMock(side_effect=capture_add)
    mock_session.refresh = AsyncMock(side_effect=lambda t: None)

    engine = LabelingEngine()
    data = TaskCreate(
        name="Sentiment Task",
        description="Label sentiment",
        task_type="classification",
        label_options=["positive", "negative"],
    )

    result = await engine.create_task("ven-1", data)

    assert result.name == "Sentiment Task"
    assert result.task_type == "classification"
    mock_event_bus.publish.assert_awaited()


@pytest.mark.asyncio
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_session")
async def test_add_items(mock_get_session, mock_session):
    """Test adding items to a labeling task."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

    task = _make_task(total_items=0)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = task
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = LabelingEngine()
    request = AddItemsRequest(
        task_id="task-1",
        items=[
            {"text": "Item 1"},
            {"text": "Item 2"},
            {"text": "Item 3"},
        ],
    )

    result = await engine.add_items("ven-1", request)

    assert result.items_added == 3
    assert result.task_id == "task-1"
    # Task total_items should be updated
    assert task.total_items == 3


@pytest.mark.asyncio
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_event_bus")
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_tracer")
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_session")
async def test_label_item_consensus(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that labeling an item resolves consensus when annotators agree."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Item already has one "positive" label, adding a second "positive"
    existing_labels = [{"annotator_id": "a1", "label": "positive", "confidence": 1.0, "notes": ""}]
    item = _make_label_item(labels=existing_labels, status="pending")

    # Also mock task for labeled_items update
    task = _make_task(labeled_items=0)

    mock_item_result = MagicMock()
    mock_item_result.scalar_one.return_value = item

    mock_task_result = MagicMock()
    mock_task_result.scalar_one.return_value = task

    call_count = [0]

    async def mock_execute(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_item_result
        return mock_task_result

    mock_session.execute = AsyncMock(side_effect=mock_execute)
    mock_session.refresh = AsyncMock(side_effect=lambda i: None)

    engine = LabelingEngine()
    request = LabelRequest(
        item_id="item-1",
        annotator_id="a2",
        label="positive",
    )

    await engine.label_item("ven-1", request)

    # Consensus should be reached (2/2 agree on "positive")
    assert item.consensus_label == "positive"
    assert item.status == "labeled"


@pytest.mark.asyncio
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_event_bus")
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_tracer")
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_session")
async def test_label_item_disputed(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that labeling an item marks it as disputed when annotators disagree."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Item has one "positive" label, we add "negative" — 50/50 = disputed
    existing_labels = [{"annotator_id": "a1", "label": "positive", "confidence": 1.0, "notes": ""}]
    item = _make_label_item(labels=existing_labels, status="pending")

    task = _make_task(labeled_items=0)

    mock_item_result = MagicMock()
    mock_item_result.scalar_one.return_value = item

    mock_task_result = MagicMock()
    mock_task_result.scalar_one.return_value = task

    call_count = [0]

    async def mock_execute(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_item_result
        return mock_task_result

    mock_session.execute = AsyncMock(side_effect=mock_execute)
    mock_session.refresh = AsyncMock(side_effect=lambda i: None)

    engine = LabelingEngine()
    request = LabelRequest(
        item_id="item-1",
        annotator_id="a2",
        label="negative",
    )

    await engine.label_item("ven-1", request)

    # 1 positive + 1 negative = tie → disputed
    assert item.status == "disputed"


@pytest.mark.asyncio
@patch("ai_flywheel.modules.data_knowledge.labeling.service.get_session")
async def test_compute_agreement(mock_get_session, mock_session):
    """Test computing inter-annotator agreement metrics."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

    # 3 items: 2 with consensus, 1 disputed
    item1 = _make_label_item(
        id_="i1",
        labels=[
            {"annotator_id": "a1", "label": "pos"},
            {"annotator_id": "a2", "label": "pos"},
        ],
    )
    item2 = _make_label_item(
        id_="i2",
        labels=[
            {"annotator_id": "a1", "label": "neg"},
            {"annotator_id": "a2", "label": "neg"},
        ],
    )
    item3 = _make_label_item(
        id_="i3",
        labels=[
            {"annotator_id": "a1", "label": "pos"},
            {"annotator_id": "a2", "label": "neg"},
        ],
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [item1, item2, item3]
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = LabelingEngine()
    metrics = await engine.compute_agreement("ven-1", "task-1")

    assert metrics.total_items == 3
    assert metrics.items_with_consensus == 2
    assert metrics.items_disputed == 1
    # Agreement rate: 2/3 multi-annotated items agree
    assert metrics.agreement_rate == pytest.approx(2 / 3, abs=0.01)
