# ruff: noqa: E501
"""Unit tests for the Memory Engine service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.agent_runtime.memory_engine.schemas import (
    ConsolidateRequest,
    MemoryContext,
    MemoryQuery,
    MemoryStore,
)
from ai_flywheel.modules.agent_runtime.memory_engine.service import (
    MemoryEngine,
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


def _make_memory_entry(
    id_="mem-1",
    venture_id="ven-1",
    agent_id="agent-1",
    tier="episodic",
    content="Hello world",
    importance=0.7,
    access_count=0,
):
    """Create a mock MemoryEntry ORM object."""
    entry = MagicMock()
    entry.id = id_
    entry.venture_id = venture_id
    entry.agent_id = agent_id
    entry.memory_tier = tier
    entry.content = content
    entry.summary = None
    entry.importance = importance
    entry.access_count = access_count
    entry.metadata_ = {}
    entry.created_at = datetime(2024, 6, 1, tzinfo=UTC)
    entry.last_accessed_at = None
    entry.deleted_at = None
    return entry


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_session")
async def test_store_memory(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test storing a new memory entry."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=lambda e: None)

    # When session.add is called, we capture the entry
    def capture_add(obj):
        obj.id = "mem-new"
        obj.venture_id = "ven-1"
        obj.agent_id = "agent-1"
        obj.memory_tier = "working"
        obj.content = "Test content"
        obj.summary = None
        obj.importance = 0.8
        obj.access_count = 0
        obj.metadata_ = {}
        obj.created_at = datetime(2024, 6, 1, tzinfo=UTC)
        obj.last_accessed_at = None

    mock_session.add = MagicMock(side_effect=capture_add)

    engine = MemoryEngine()
    data = MemoryStore(
        agent_id="agent-1",
        tier="working",
        content="Test content",
        importance=0.8,
    )

    result = await engine.store("ven-1", data)

    assert result is not None
    mock_session.flush.assert_awaited_once()
    mock_event_bus.publish.assert_awaited_once()
    call_kwargs = mock_event_bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "memory.stored"


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_session")
async def test_recall_by_tier(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test recalling memories filtered by tier."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    entry = _make_memory_entry(tier="semantic")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [entry]
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = MemoryEngine()
    query = MemoryQuery(tier="semantic", limit=10)

    results = await engine.recall("ven-1", query)

    assert len(results) == 1
    assert results[0].memory_tier == "semantic"
    mock_event_bus.publish.assert_awaited()


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_session")
async def test_get_context_respects_budget(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that get_context fills context respecting the token budget."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Create entries with known content sizes
    # "A" * 100 = 25 tokens
    working_entry = _make_memory_entry(tier="working", content="A" * 100)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [working_entry]
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = MemoryEngine()
    # Budget of 30 tokens should fit one entry of 25 tokens
    context = await engine.get_context("ven-1", "agent-1", token_budget=30)

    assert isinstance(context, MemoryContext)
    assert context.total_tokens_estimate <= 30


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_session")
async def test_consolidate_old_memories(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test that consolidation summarizes old episodic memories."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    # Old entry without a summary
    old_entry = _make_memory_entry(tier="episodic", content="Long content " * 30)
    old_entry.summary = None
    old_entry.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [old_entry]
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = MemoryEngine()
    request = ConsolidateRequest(venture_id="ven-1", max_age_hours=24)

    count = await engine.consolidate("ven-1", request)

    assert count == 1
    # Summary should have been set (truncated to 200 chars)
    assert old_entry.summary is not None
    assert len(old_entry.summary) <= 200
    mock_event_bus.publish.assert_awaited()


@pytest.mark.asyncio
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.memory_engine.service.get_session")
async def test_forget_memory(mock_get_session, mock_get_tracer, mock_get_event_bus, mock_session, mock_tracer, mock_event_bus):
    """Test soft-deleting a memory."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer
    mock_get_event_bus.return_value = mock_event_bus

    entry = _make_memory_entry()
    entry.deleted_at = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = entry
    mock_session.execute = AsyncMock(return_value=mock_result)

    engine = MemoryEngine()
    await engine.forget("ven-1", "mem-1")

    # Entry should have been soft-deleted
    assert entry.deleted_at is not None
    mock_event_bus.publish.assert_awaited()
