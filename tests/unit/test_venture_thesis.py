# ruff: noqa: E501
"""Unit tests for Venture Thesis Engine — thesis lifecycle and evidence management."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.modules.product_intelligence.venture_thesis.schemas import (
    AssumptionCreate,
    ThesisCreate,
    ThesisMemoRequest,
)
from ai_flywheel.modules.product_intelligence.venture_thesis.service import (
    VentureThesisEngine,
    _derive_assumption_status,
    _update_confidence,
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


@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_session")
@pytest.mark.asyncio
async def test_create_thesis_with_assumptions(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """create_thesis should create thesis with assumptions and emit event."""
    obj_counter = [0]

    def add_side_effect(obj):
        obj_counter[0] += 1
        obj.id = f"obj-{obj_counter[0]:03d}"
        obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        if hasattr(obj, "confidence") and not hasattr(obj, "hypothesis"):
            # It's an assumption
            obj.status = "untested"
            obj.confidence = 0.5
            obj.evidence = []
            obj.experiment_ids = []

    mock_session.add.side_effect = add_side_effect

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    engine = VentureThesisEngine()
    data = ThesisCreate(
        title="AI Tutoring Thesis",
        hypothesis="We believe AI tutoring will improve student outcomes because personalization is effective",
        assumptions=[
            AssumptionCreate(statement="Students want personalized learning", risk_level="high"),
            AssumptionCreate(statement="AI can personalize effectively", risk_level="medium"),
        ],
        kill_signals=["No student engagement after 30 days"],
    )
    result = await engine.create_thesis("ven-001", data)

    assert result.title == "AI Tutoring Thesis"
    assert len(result.assumptions) == 2
    assert result.assumptions[0].statement == "Students want personalized learning"
    assert result.kill_signals == ["No student engagement after 30 days"]
    mock_event_bus.publish.assert_awaited_once()
    call_kwargs = mock_event_bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "thesis.created"


def test_add_evidence_updates_confidence_supports():
    """_update_confidence should increase confidence when direction is 'supports'."""
    current = 0.5
    updated = _update_confidence(current, "supports", strength=0.8)

    # Should move toward 1.0: 0.5 + (1.0 - 0.5) * 0.8 * 0.3 = 0.5 + 0.12 = 0.62
    expected = 0.5 + (1.0 - 0.5) * 0.8 * 0.3
    assert abs(updated - expected) < 0.001
    assert updated > current


def test_add_evidence_updates_confidence_contradicts():
    """_update_confidence should decrease confidence when direction is 'contradicts'."""
    current = 0.5
    updated = _update_confidence(current, "contradicts", strength=0.8)

    # Should move toward 0.0: 0.5 - 0.5 * 0.8 * 0.3 = 0.5 - 0.12 = 0.38
    expected = 0.5 - 0.5 * 0.8 * 0.3
    assert abs(updated - expected) < 0.001
    assert updated < current

    # Neutral should not change
    unchanged = _update_confidence(current, "neutral", strength=0.8)
    assert unchanged == current


def test_assumption_auto_validates_at_high_confidence():
    """_derive_assumption_status should return 'validated' when confidence > 0.8."""
    assert _derive_assumption_status(0.85, evidence_count=3) == "validated"
    assert _derive_assumption_status(0.15, evidence_count=3) == "invalidated"
    assert _derive_assumption_status(0.5, evidence_count=2) == "testing"
    assert _derive_assumption_status(0.5, evidence_count=0) == "untested"


@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_session")
@pytest.mark.asyncio
async def test_check_kill_signals_triggers(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """check_kill_signals should trigger when an assumption confidence drops below 0.2."""
    # Mock thesis with kill signals
    mock_thesis = MagicMock()
    mock_thesis.id = "thesis-001"
    mock_thesis.venture_id = "ven-001"
    mock_thesis.kill_signals = ["Market too small", "No user engagement"]
    mock_thesis.deleted_at = None

    # Mock an assumption with very low confidence (invalidated)
    mock_assumption = MagicMock()
    mock_assumption.id = "asmp-001"
    mock_assumption.statement = "Users want this product"
    mock_assumption.confidence = 0.1  # Below 0.2 threshold
    mock_assumption.deleted_at = None

    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Thesis query
            result.scalar_one.return_value = mock_thesis
        elif call_count[0] == 2:
            # Assumptions query
            result.scalars.return_value.all.return_value = [mock_assumption]
        return result

    mock_session.execute = AsyncMock(side_effect=execute_side_effect)

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    engine = VentureThesisEngine()
    triggered = await engine.check_kill_signals("ven-001", "thesis-001")

    assert len(triggered) == 2
    assert "Market too small" in triggered
    assert "No user engagement" in triggered
    # Should have emitted kill signal events
    assert mock_event_bus.publish.await_count == 2


@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.generate")
@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.venture_thesis.service.get_session")
@pytest.mark.asyncio
async def test_generate_memo_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer
):
    """generate_memo should call LLM and return structured memo."""
    # Mock thesis
    mock_thesis = MagicMock()
    mock_thesis.id = "thesis-001"
    mock_thesis.venture_id = "ven-001"
    mock_thesis.title = "AI Tutoring"
    mock_thesis.hypothesis = "AI tutoring improves outcomes"
    mock_thesis.status = "active"
    mock_thesis.confidence = 0.65
    mock_thesis.evidence_count = 5
    mock_thesis.kill_signals = ["No engagement"]
    mock_thesis.deleted_at = None

    # Mock assumption
    mock_assumption = MagicMock()
    mock_assumption.id = "asmp-001"
    mock_assumption.thesis_id = "thesis-001"
    mock_assumption.statement = "Students want personalized learning"
    mock_assumption.risk_level = "high"
    mock_assumption.status = "testing"
    mock_assumption.confidence = 0.7
    mock_assumption.evidence = [{"direction": "supports", "content": "Survey confirms"}]
    mock_assumption.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    mock_assumption.deleted_at = None

    # Mock evidence
    mock_evidence = MagicMock()
    mock_evidence.id = "ev-001"
    mock_evidence.source_type = "interview"
    mock_evidence.content = "Students confirmed interest"
    mock_evidence.direction = "supports"
    mock_evidence.strength = 0.8
    mock_evidence.recorded_at = datetime(2024, 3, 1, tzinfo=UTC)
    mock_evidence.deleted_at = None

    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one.return_value = mock_thesis
        elif call_count[0] == 2:
            result.scalars.return_value.all.return_value = [mock_assumption]
        elif call_count[0] == 3:
            result.scalars.return_value.all.return_value = [mock_evidence]
        return result

    mock_session.execute = AsyncMock(side_effect=execute_side_effect)

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    memo_json = json.dumps({
        "memo": "# AI Tutoring Venture Memo\n\nThis thesis shows moderate confidence...",
        "confidence_summary": {
            "Students want personalized learning": 0.7,
        },
        "next_actions": ["Run 5 more user interviews", "Build MVP prototype"],
    })
    mock_generate.return_value = LLMResponse(
        content=memo_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=600,
        tokens_output=500,
        cost_usd=0.007,
    )

    engine = VentureThesisEngine()
    request = ThesisMemoRequest(thesis_id="thesis-001")
    result = await engine.generate_memo("ven-001", request)

    mock_generate.assert_awaited_once()
    assert "AI Tutoring" in result.memo
    assert result.thesis_id == "thesis-001"
    assert len(result.next_actions) == 2
    assert result.confidence_summary["Students want personalized learning"] == 0.7
