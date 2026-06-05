"""Unit tests for WorkflowBlueprintEngine service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.modules.product_intelligence.workflow_blueprint.schemas import (
    BlueprintCreate,
    CompileRequest,
    GenerateBlueprintRequest,
    ValidateBlueprintRequest,
)
from ai_flywheel.modules.product_intelligence.workflow_blueprint.service import (
    WorkflowBlueprintEngine,
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

    mock_span = MagicMock()
    mock_span.set_cost = MagicMock()
    mock_span.metadata = {}
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm

    return tracer


@pytest.fixture
def fake_blueprint():
    """Create a fake WorkflowBlueprint ORM object."""
    bp = MagicMock()
    bp.id = "bp-001"
    bp.venture_id = "ven-001"
    bp.name = "Customer Onboarding"
    bp.description = "Onboarding workflow"
    bp.status = "draft"
    bp.nodes = [
        {"id": "start_1", "name": "Start", "type": "start", "config": {}, "inputs": [], "outputs": [], "sla_seconds": None},
        {"id": "agent_1", "name": "Welcome Email", "type": "ai_agent", "config": {"agent_id": "email-agent"}, "inputs": [], "outputs": ["email_sent"], "sla_seconds": None},
        {"id": "human_1", "name": "Manual Review", "type": "human", "config": {"approval_required": True}, "inputs": ["email_sent"], "outputs": ["approved"], "sla_seconds": 3600},
        {"id": "tool_1", "name": "CRM Update", "type": "tool", "config": {"tool_id": "crm-update"}, "inputs": ["approved"], "outputs": [], "sla_seconds": None},
        {"id": "end_1", "name": "End", "type": "end", "config": {}, "inputs": [], "outputs": [], "sla_seconds": None},
    ]
    bp.edges = [
        {"source_node_id": "start_1", "target_node_id": "agent_1", "condition": None},
        {"source_node_id": "agent_1", "target_node_id": "human_1", "condition": None},
        {"source_node_id": "human_1", "target_node_id": "tool_1", "condition": None},
        {"source_node_id": "tool_1", "target_node_id": "end_1", "condition": None},
    ]
    bp.sla_config = None
    bp.fallback_config = None
    bp.version = 1
    bp.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    bp.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    bp.deleted_at = None
    return bp


@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_session")
async def test_create_blueprint(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer,
):
    """create_blueprint should persist an empty blueprint and emit event."""
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
                obj.id = "bp-001"
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)
            if hasattr(obj, "updated_at") and obj.updated_at is None:
                obj.updated_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    engine = WorkflowBlueprintEngine()
    data = BlueprintCreate(name="Customer Onboarding", description="Onboarding workflow")
    result = await engine.create_blueprint("ven-001", data)

    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "workflow.blueprint.created"
    assert publish_kwargs["venture_id"] == "ven-001"


@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.generate")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_session")
async def test_generate_from_description_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer,
):
    """generate_from_description should call LLM and persist the generated workflow."""
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
                obj.id = "bp-002"

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    workflow_data = {
        "nodes": [
            {"id": "node_1", "name": "Start", "type": "start", "config": {}, "inputs": [], "outputs": [], "sla_seconds": None},
            {"id": "node_2", "name": "Analyze", "type": "ai_agent", "config": {"agent_id": "analyzer"}, "inputs": [], "outputs": ["analysis"], "sla_seconds": None},
            {"id": "node_3", "name": "End", "type": "end", "config": {}, "inputs": [], "outputs": [], "sla_seconds": None},
        ],
        "edges": [
            {"source_node_id": "node_1", "target_node_id": "node_2", "condition": None},
            {"source_node_id": "node_2", "target_node_id": "node_3", "condition": None},
        ],
        "summary": "Simple analysis workflow",
    }
    mock_generate.return_value = LLMResponse(
        content=json.dumps(workflow_data),
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=200,
        tokens_output=400,
        cost_usd=0.003,
    )

    engine = WorkflowBlueprintEngine()
    request = GenerateBlueprintRequest(
        name="Data Analysis Pipeline",
        process_description="Analyze incoming data and produce a report",
    )
    result = await engine.generate_from_description("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.blueprint_id == "bp-002"
    assert len(result.nodes) == 3
    assert result.ai_steps == 1
    assert result.human_steps == 0


@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_session")
async def test_validate_detects_orphan_nodes(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer,
):
    """validate should detect nodes not reachable from start (orphans)."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Blueprint with an orphan node
    bp = MagicMock()
    bp.nodes = [
        {"id": "start_1", "name": "Start", "type": "start", "config": {}},
        {"id": "step_1", "name": "Step 1", "type": "ai_agent", "config": {}},
        {"id": "orphan_1", "name": "Orphan", "type": "tool", "config": {}},
        {"id": "end_1", "name": "End", "type": "end", "config": {}},
    ]
    bp.edges = [
        {"source_node_id": "start_1", "target_node_id": "step_1"},
        {"source_node_id": "step_1", "target_node_id": "end_1"},
        # orphan_1 has no incoming edges from the main flow
    ]
    bp.deleted_at = None

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = bp
    mock_session.execute.return_value = mock_result

    engine = WorkflowBlueprintEngine()
    request = ValidateBlueprintRequest(blueprint_id="bp-001")
    result = await engine.validate("ven-001", request)

    assert result.is_valid is False
    # Should detect orphan node as unreachable
    assert any("orphan_1" in err for err in result.errors)


@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_session")
async def test_validate_detects_cycles(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer,
):
    """validate should detect cycles in the workflow graph."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Blueprint with a cycle: step_1 → step_2 → step_1
    bp = MagicMock()
    bp.nodes = [
        {"id": "start_1", "name": "Start", "type": "start", "config": {}},
        {"id": "step_1", "name": "Step 1", "type": "ai_agent", "config": {}},
        {"id": "step_2", "name": "Step 2", "type": "tool", "config": {}},
        {"id": "end_1", "name": "End", "type": "end", "config": {}},
    ]
    bp.edges = [
        {"source_node_id": "start_1", "target_node_id": "step_1"},
        {"source_node_id": "step_1", "target_node_id": "step_2"},
        {"source_node_id": "step_2", "target_node_id": "step_1"},  # cycle!
        {"source_node_id": "step_2", "target_node_id": "end_1"},
    ]
    bp.deleted_at = None

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = bp
    mock_session.execute.return_value = mock_result

    engine = WorkflowBlueprintEngine()
    request = ValidateBlueprintRequest(blueprint_id="bp-001")
    result = await engine.validate("ven-001", request)

    assert result.is_valid is False
    assert any("cycle" in err.lower() for err in result.errors)


@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.workflow_blueprint.service.get_session")
async def test_compile_extracts_agents_and_tools(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_blueprint,
):
    """compile should extract agents_required and tools_required from nodes."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_blueprint
    mock_session.execute.return_value = mock_result

    engine = WorkflowBlueprintEngine()
    request = CompileRequest(blueprint_id="bp-001")
    result = await engine.compile("ven-001", request)

    assert result.blueprint_id == "bp-001"
    assert "email-agent" in result.agents_required
    assert "crm-update" in result.tools_required
    assert "steps" in result.temporal_workflow_config
    assert result.temporal_workflow_config["workflow_name"] == "Customer Onboarding"
