"""Unit tests for AgentFactory service."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.modules.agent_runtime.agent_factory.schemas import (
    AgentBlueprintCreate,
    AgentBlueprintUpdate,
    AgentExecutionRequest,
)
from ai_flywheel.modules.agent_runtime.agent_factory.service import AgentFactory


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
    tracer.start_trace.return_value = "trace-001"
    tracer.set_venture_context = MagicMock()

    # Mock span as an async context manager
    mock_span = MagicMock()
    mock_span.set_cost = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm

    return tracer


@pytest.fixture
def fake_blueprint():
    """Create a fake AgentBlueprint ORM object."""
    bp = MagicMock()
    bp.id = "agent-001"
    bp.venture_id = "ven-001"
    bp.name = "test-agent"
    bp.description = "A test agent"
    bp.agent_type = "single"
    bp.model = "gpt-4o-mini"
    bp.system_prompt = "You are a helpful assistant."
    bp.tools = []
    bp.memory_tiers = {}
    bp.max_tokens = 4096
    bp.temperature = 0.7
    bp.timeout_seconds = 120
    bp.retry_policy = {"maximum_attempts": 3, "backoff_coefficient": 2.0}
    bp.is_active = True
    bp.version = 1
    bp.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    bp.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    bp.deleted_at = None
    return bp


@pytest.fixture
def mock_llm_response():
    """Pre-made LLM response."""
    return LLMResponse(
        content="Hello! How can I help you today?",
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=50,
        tokens_output=20,
        cost_usd=0.001,
        cached=False,
        latency_ms=200.0,
    )


@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_session")
async def test_create_agent_persists_blueprint(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_blueprint
):
    """create_agent should persist a blueprint and emit agent.created event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    with patch(
        "ai_flywheel.modules.agent_runtime.agent_factory.service.AgentBlueprintResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "agent-001"
        mock_resp.name = "test-agent"
        mock_resp.agent_type = "single"
        MockResponse.model_validate.return_value = mock_resp

        factory = AgentFactory()
        data = AgentBlueprintCreate(
            name="test-agent",
            description="A test agent",
            agent_type="single",
            model="gpt-4o-mini",
            system_prompt="You are helpful.",
        )
        result = await factory.create_agent("ven-001", data)

    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "agent.created"
    assert publish_kwargs["payload"]["name"] == "test-agent"


@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_session")
async def test_get_agent_returns_correct_data(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_blueprint
):
    """get_agent should return the blueprint response for a valid agent_id."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_blueprint
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_flywheel.modules.agent_runtime.agent_factory.service.AgentBlueprintResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "agent-001"
        mock_resp.name = "test-agent"
        mock_resp.agent_type = "single"
        mock_resp.model = "gpt-4o-mini"
        MockResponse.model_validate.return_value = mock_resp

        factory = AgentFactory()
        result = await factory.get_agent("ven-001", "agent-001")

    assert result.id == "agent-001"
    assert result.name == "test-agent"
    assert result.agent_type == "single"


@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.generate")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_session")
async def test_execute_single_agent_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_blueprint, mock_llm_response
):
    """execute with single agent_type should call LLM and return result."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer
    mock_generate.return_value = mock_llm_response

    # Mock get_agent to return a response object
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_blueprint
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_flywheel.modules.agent_runtime.agent_factory.service.AgentBlueprintResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "agent-001"
        mock_resp.name = "test-agent"
        mock_resp.agent_type = "single"
        mock_resp.model = "gpt-4o-mini"
        mock_resp.system_prompt = "You are a helpful assistant."
        mock_resp.max_tokens = 4096
        mock_resp.temperature = 0.7
        mock_resp.model_dump = MagicMock(return_value={})
        MockResponse.model_validate.return_value = mock_resp

        factory = AgentFactory()
        request = AgentExecutionRequest(
            agent_id="agent-001",
            task="Say hello",
        )
        result = await factory.execute("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.status == "completed"
    assert result.output == "Hello! How can I help you today?"
    assert result.cost_usd == 0.001
    assert result.tokens_input == 50
    assert result.tokens_output == 20


@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_session")
async def test_update_agent_increments_version(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_blueprint
):
    """update_agent should increment version when fields are changed."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_blueprint
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_flywheel.modules.agent_runtime.agent_factory.service.AgentBlueprintResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "agent-001"
        mock_resp.name = "updated-agent"
        mock_resp.version = 2
        MockResponse.model_validate.return_value = mock_resp

        factory = AgentFactory()
        data = AgentBlueprintUpdate(name="updated-agent", temperature=0.5)
        result = await factory.update_agent("ven-001", "agent-001", data)

    # Version should have been incremented on the blueprint object
    assert fake_blueprint.version == 2
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "agent.updated"
    assert publish_kwargs["payload"]["version"] == 2


@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_tracer")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.agent_factory.service.get_session")
async def test_execute_raises_without_agent_id_or_name(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """execute should raise ValueError if neither agent_id nor agent_name provided."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    factory = AgentFactory()
    request = AgentExecutionRequest(task="Do something")

    with pytest.raises(ValueError, match="Either agent_id or agent_name"):
        await factory.execute("ven-001", request)
