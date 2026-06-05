"""Unit tests for ToolForge service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ai_flywheel.modules.agent_runtime.tool_forge.schemas import (
    ToolCreate,
    ToolInvokeRequest,
    ToolSearchRequest,
)
from ai_flywheel.modules.agent_runtime.tool_forge.service import ToolForge


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
    mock_span.set_error = MagicMock()
    mock_span.metadata = {}
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm

    return tracer


@pytest.fixture
def fake_tool():
    """Create a fake ToolDefinition ORM object."""
    tool = MagicMock()
    tool.id = "tool-001"
    tool.venture_id = "ven-001"
    tool.name = "stripe-charge"
    tool.description = "Create a Stripe charge"
    tool.category = "payment"
    tool.input_schema = {"amount": "integer", "currency": "string"}
    tool.output_schema = {"charge_id": "string"}
    tool.config = {
        "base_url": "https://api.stripe.com",
        "method": "POST",
        "path": "/v1/charges",
        "auth_type": "bearer",
        "api_key": "sk_test_xxx",
    }
    tool.version = 1
    tool.is_active = True
    tool.reliability_score = 1.0
    tool.avg_latency_ms = 0.0
    tool.total_invocations = 0
    tool.failure_count = 0
    tool.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    tool.deleted_at = None
    return tool


@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_session")
async def test_register_tool(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_tool,
):
    """register_tool should persist tool and emit tool.registered event."""
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
                obj.id = "tool-001"
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)
            # Set defaults for model_validate
            if hasattr(obj, "version") and obj.version is None:
                obj.version = 1
            if hasattr(obj, "is_active") and obj.is_active is None:
                obj.is_active = True
            if hasattr(obj, "reliability_score") and obj.reliability_score is None:
                obj.reliability_score = 1.0
            if hasattr(obj, "avg_latency_ms") and obj.avg_latency_ms is None:
                obj.avg_latency_ms = 0.0
            if hasattr(obj, "total_invocations") and obj.total_invocations is None:
                obj.total_invocations = 0

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    forge = ToolForge()
    data = ToolCreate(
        name="stripe-charge",
        description="Create a Stripe charge",
        category="payment",
        input_schema={"amount": "integer", "currency": "string"},
        config={"base_url": "https://api.stripe.com", "method": "POST", "path": "/v1/charges"},
    )
    result = await forge.register_tool("ven-001", data)

    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "tool.registered"
    assert publish_kwargs["payload"]["name"] == "stripe-charge"


@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_session")
async def test_invoke_tool_success(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_tool,
):
    """invoke should make HTTP request and return success result."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Mock DB queries: first get_tool_by_name, then _record_execution, then _update_tool_stats
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_tool
    mock_session.execute.return_value = mock_result

    # Mock execution ID assignment on flush
    execution_objs = []
    original_add = mock_session.add

    def add_with_tracking(obj):
        execution_objs.append(obj)

    mock_session.add.side_effect = add_with_tracking

    async def flush_with_id():
        for obj in execution_objs:
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = "exec-001"

    mock_session.flush = AsyncMock(side_effect=flush_with_id)

    # Mock httpx
    mock_response = MagicMock()
    mock_response.json.return_value = {"charge_id": "ch_123"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        forge = ToolForge()
        request = ToolInvokeRequest(
            tool_name="stripe-charge",
            parameters={"amount": 2000, "currency": "usd"},
            agent_id="agent-001",
        )
        result = await forge.invoke("ven-001", request)

    assert result.status == "success"
    assert result.output == {"charge_id": "ch_123"}
    assert result.error is None
    assert result.execution_id == "exec-001"


@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_session")
async def test_invoke_tool_timeout(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_tool,
):
    """invoke should handle timeout and record failure."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_tool
    mock_session.execute.return_value = mock_result

    execution_objs = []

    def add_with_tracking(obj):
        execution_objs.append(obj)

    mock_session.add.side_effect = add_with_tracking

    async def flush_with_id():
        for obj in execution_objs:
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = "exec-002"

    mock_session.flush = AsyncMock(side_effect=flush_with_id)

    # Mock httpx to raise timeout
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        forge = ToolForge()
        request = ToolInvokeRequest(
            tool_name="stripe-charge",
            parameters={"amount": 2000, "currency": "usd"},
            timeout_ms=5000,
        )
        result = await forge.invoke("ven-001", request)

    assert result.status == "timeout"
    assert result.output is None
    assert "timed out" in result.error


@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_session")
async def test_search_by_keyword(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_tool,
):
    """search should query tools by keyword and return matches."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_tool]
    mock_session.execute.return_value = mock_result

    forge = ToolForge()
    request = ToolSearchRequest(query="stripe", category="payment")
    result = await forge.search("ven-001", request)

    assert result.query == "stripe"
    assert len(result.tools) == 1
    assert result.tools[0].name == "stripe-charge"


@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.tool_forge.service.get_session")
async def test_reliability_score_updates(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_tool,
):
    """_update_tool_stats should update reliability score after invocations."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Set up tool with some history
    fake_tool.total_invocations = 9
    fake_tool.failure_count = 1
    fake_tool.reliability_score = 0.89
    fake_tool.avg_latency_ms = 100.0

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_tool
    mock_session.execute.return_value = mock_result

    forge = ToolForge()
    # Simulate a failure invocation
    await forge._update_tool_stats(
        venture_id="ven-001",
        tool_id="tool-001",
        status="failure",
        duration_ms=250.0,
    )

    # After: total_invocations=10, failure_count=2
    assert fake_tool.total_invocations == 10
    assert fake_tool.failure_count == 2
    assert fake_tool.reliability_score == 0.8  # 1 - 2/10
