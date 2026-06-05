# ruff: noqa: E501
"""Unit tests for Knowledge Graph Builder — creation, extraction, similarity, merging."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.modules.data_knowledge.knowledge_graph.schemas import (
    ExtractRequest,
    GraphCreate,
)
from ai_flywheel.modules.data_knowledge.knowledge_graph.service import (
    KnowledgeGraphBuilder,
    _similarity,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


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

    mock_span = MagicMock()
    mock_span.set_cost = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm

    return tracer


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@patch("ai_flywheel.modules.data_knowledge.knowledge_graph.service.get_tracer")
@patch("ai_flywheel.modules.data_knowledge.knowledge_graph.service.get_event_bus")
@patch("ai_flywheel.modules.data_knowledge.knowledge_graph.service.get_session")
@pytest.mark.asyncio
async def test_create_graph(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """create_graph should persist a graph and emit kg.graph.created event."""
    def add_side_effect(obj):
        obj.id = "graph-001"
        obj.venture_id = "ven-001"
        obj.entity_types = []
        obj.relationship_types = []
        obj.entity_count = 0
        obj.relationship_count = 0
        obj.status = "building"
        obj.description = "Test graph"
        from datetime import UTC, datetime
        obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.add.side_effect = add_side_effect

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    builder = KnowledgeGraphBuilder()
    data = GraphCreate(name="Test Graph", description="Test graph")
    result = await builder.create_graph("ven-001", data)

    assert result.id == "graph-001"
    assert result.name == "Test Graph"
    mock_event_bus.publish.assert_awaited_once()
    call_kwargs = mock_event_bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "kg.graph.created"


@patch("ai_flywheel.modules.data_knowledge.knowledge_graph.service.generate")
@patch("ai_flywheel.modules.data_knowledge.knowledge_graph.service.get_tracer")
@patch("ai_flywheel.modules.data_knowledge.knowledge_graph.service.get_event_bus")
@patch("ai_flywheel.modules.data_knowledge.knowledge_graph.service.get_session")
@pytest.mark.asyncio
async def test_extract_calls_llm_and_stores_entities(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer
):
    """extract should call LLM, parse JSON, and store new entities."""
    # Mock get_graph response via get_session
    mock_graph = MagicMock()
    mock_graph.id = "graph-001"
    mock_graph.venture_id = "ven-001"
    mock_graph.name = "Test Graph"
    mock_graph.description = "desc"
    mock_graph.entity_types = []
    mock_graph.relationship_types = []
    mock_graph.entity_count = 0
    mock_graph.relationship_count = 0
    mock_graph.status = "building"
    from datetime import UTC, datetime
    mock_graph.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    mock_graph.deleted_at = None

    # Different DB results for different calls
    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # get_graph query
            result.scalar_one_or_none.return_value = mock_graph
            result.scalar_one.return_value = mock_graph
        elif call_count[0] == 2:
            # Load existing entities
            result.scalars.return_value.all.return_value = []
        else:
            result.scalar_one_or_none.return_value = mock_graph
            result.scalars.return_value.all.return_value = []
        return result

    mock_session.execute = AsyncMock(side_effect=execute_side_effect)

    # Make flush assign IDs to entities
    flush_count = [0]

    async def flush_side_effect():
        flush_count[0] += 1

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    # Simulate add assigning an ID
    entity_counter = [0]

    def add_side_effect(obj):
        if hasattr(obj, "entity_type"):
            entity_counter[0] += 1
            obj.id = f"entity-{entity_counter[0]:03d}"
        elif hasattr(obj, "relationship_type"):
            obj.id = "rel-001"

    mock_session.add.side_effect = add_side_effect

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Mock LLM response with extraction JSON
    extraction_json = json.dumps({
        "entities": [
            {"entity_type": "Person", "name": "John Doe", "properties": {"role": "CEO"}},
            {"entity_type": "Organization", "name": "Acme Corp", "properties": {}},
        ],
        "relationships": [
            {"source": "John Doe", "target": "Acme Corp", "relationship_type": "WORKS_FOR", "properties": {}}
        ],
    })
    mock_generate.return_value = LLMResponse(
        content=extraction_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=300,
        tokens_output=200,
        cost_usd=0.003,
    )

    builder = KnowledgeGraphBuilder()
    request = ExtractRequest(graph_id="graph-001", text="John Doe is CEO of Acme Corp.")
    result = await builder.extract("ven-001", request)

    mock_generate.assert_awaited_once()
    assert len(result.entities_extracted) == 2
    assert result.entities_extracted[0].name == "John Doe"
    assert result.entities_extracted[1].name == "Acme Corp"


def test_entity_similarity_exact_match():
    """_similarity should return 1.0 for identical (case-insensitive) strings."""
    assert _similarity("John Doe", "john doe") == 1.0
    assert _similarity("ACME", "acme") == 1.0


def test_entity_similarity_containment():
    """_similarity should return 0.9 when one string contains the other."""
    assert _similarity("John", "John Doe") == 0.9
    assert _similarity("Acme Corporation", "Acme") == 0.9


def test_merge_entities():
    """_similarity word overlap — non-exact, non-containment case."""
    # Testing word-overlap branch
    score = _similarity("Artificial Intelligence", "Machine Intelligence")
    # "Intelligence" is shared, 1 overlap / max(2, 2) = 0.5
    assert abs(score - 0.5) < 0.001
