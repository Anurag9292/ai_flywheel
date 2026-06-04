"""Tests for inter-module contracts."""

from datetime import UTC, datetime

from ai_flywheel.core.contracts.events import (
    AgentCompletedEvent,
    LLMCallCompletedEvent,
    VentureCreatedEvent,
)
from ai_flywheel.core.contracts.schemas import LLMRequest, LLMResponse


def test_llm_request_defaults():
    """LLMRequest should have sensible defaults."""
    req = LLMRequest(messages=[{"role": "user", "content": "hi"}])
    assert req.model == "gpt-4o-mini"
    assert req.temperature == 0.7
    assert req.max_tokens is None


def test_llm_response_serialization():
    """LLMResponse should serialize cleanly."""
    resp = LLMResponse(
        content="Hello!",
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=10,
        tokens_output=5,
        cost_usd=0.001,
    )
    d = resp.model_dump()
    assert d["content"] == "Hello!"
    assert d["cached"] is False


def test_agent_completed_event():
    """AgentCompletedEvent should validate correctly."""
    event = AgentCompletedEvent(
        agent_id="agent-1",
        venture_id="venture-1",
        task_id="task-1",
        duration_ms=340.5,
        cost_usd=0.03,
        tokens_input=150,
        tokens_output=50,
        model_used="gpt-4o",
        timestamp=datetime.now(UTC),
    )
    assert event.agent_id == "agent-1"
    assert event.cost_usd == 0.03


def test_venture_created_event():
    """VentureCreatedEvent should validate correctly."""
    event = VentureCreatedEvent(
        venture_id="v-1",
        name="MatchHire",
        domain="AI hiring marketplace",
        timestamp=datetime.now(UTC),
    )
    assert event.name == "MatchHire"
