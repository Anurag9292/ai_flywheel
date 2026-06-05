# ruff: noqa: E501
"""Unit tests for Market & Signal Intelligence service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.modules.product_intelligence.market_intelligence.schemas import (
    AnalyzeSignalsRequest,
    MarketReportRequest,
    SignalSourceCreate,
)
from ai_flywheel.modules.product_intelligence.market_intelligence.service import (
    MarketIntelligence,
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


@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_session")
@pytest.mark.asyncio
async def test_create_source(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """create_source should persist a signal source and emit event."""
    def add_side_effect(obj):
        obj.id = "src-001"
        obj.venture_id = "ven-001"
        obj.is_active = True
        obj.last_scanned_at = None
        obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.add.side_effect = add_side_effect

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    service = MarketIntelligence()
    data = SignalSourceCreate(
        name="TechCrunch",
        source_type="news",
        url="https://techcrunch.com",
    )
    result = await service.create_source("ven-001", data)

    assert result.id == "src-001"
    assert result.name == "TechCrunch"
    mock_event_bus.publish.assert_awaited_once()
    call_kwargs = mock_event_bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "market.source.created"


@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.generate")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_session")
@pytest.mark.asyncio
async def test_analyze_signals_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer
):
    """analyze_signals should call LLM and return parsed signals."""
    signal_counter = [0]

    def add_side_effect(obj):
        signal_counter[0] += 1
        obj.id = f"sig-{signal_counter[0]:03d}"
        obj.detected_at = datetime(2024, 6, 1, tzinfo=UTC)

    mock_session.add.side_effect = add_side_effect

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Mock LLM response
    analysis_json = json.dumps({
        "signals": [
            {
                "signal_type": "competitor_move",
                "title": "Competitor launched AI feature",
                "summary": "Major competitor released a new AI-powered feature targeting our market.",
                "relevance_score": 0.85,
                "impact_score": 0.7,
                "tags": ["ai", "competition"],
            }
        ],
        "patterns": ["AI acceleration in market"],
        "summary": "The market is seeing increased AI adoption.",
    })
    mock_generate.return_value = LLMResponse(
        content=analysis_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=400,
        tokens_output=300,
        cost_usd=0.004,
    )

    service = MarketIntelligence()
    request = AnalyzeSignalsRequest(
        venture_id="ven-001",
        domain="AI SaaS",
        signals_text="A competitor just launched a new AI feature...",
    )
    result = await service.analyze_signals("ven-001", request)

    mock_generate.assert_awaited_once()
    assert len(result.signals) == 1
    assert result.signals[0].signal_type == "competitor_move"
    assert result.summary == "The market is seeing increased AI adoption."


@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.generate")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_session")
@pytest.mark.asyncio
async def test_generate_report(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer
):
    """generate_report should synthesize signals into a report via LLM."""
    # First call returns signals, second call persists report
    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Return signals for context
            mock_signal = MagicMock()
            mock_signal.signal_type = "trend"
            mock_signal.title = "AI Growth"
            mock_signal.summary = "AI is growing fast"
            mock_signal.relevance_score = 0.9
            mock_signal.impact_score = 0.8
            mock_signal.detected_at = datetime(2024, 6, 1, tzinfo=UTC)
            result.scalars.return_value.all.return_value = [mock_signal]
        return result

    mock_session.execute = AsyncMock(side_effect=execute_side_effect)

    def add_side_effect(obj):
        obj.id = "report-001"
        obj.created_at = datetime(2024, 6, 1, tzinfo=UTC)

    mock_session.add.side_effect = add_side_effect

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    report_json = json.dumps({
        "content": "# Market Report\n\nAI continues to grow...",
        "key_findings": ["AI market growing rapidly"],
        "recommendations": ["Invest in AI capabilities"],
    })
    mock_generate.return_value = LLMResponse(
        content=report_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=500,
        tokens_output=400,
        cost_usd=0.006,
    )

    service = MarketIntelligence()
    request = MarketReportRequest(
        venture_id="ven-001",
        domain="AI SaaS",
        report_type="digest",
        period="weekly",
    )
    result = await service.generate_report("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.id == "report-001"
    assert "Market Report" in result.content
    assert len(result.key_findings) == 1


@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.generate")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_session")
@pytest.mark.asyncio
async def test_score_opportunity(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer
):
    """score_opportunity should return multi-factor scoring via LLM."""
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    score_json = json.dumps({
        "opportunity": "AI-powered document processing for SMBs",
        "market_size_signal": "large — growing TAM of $5B",
        "competition_level": "moderate — few specialized players",
        "timing": "good — market ready for disruption",
        "overall_score": 0.78,
    })
    mock_generate.return_value = LLMResponse(
        content=score_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=200,
        tokens_output=150,
        cost_usd=0.002,
    )

    service = MarketIntelligence()
    result = await service.score_opportunity(
        "ven-001",
        "AI-powered document processing for small businesses",
        "AI SaaS",
    )

    mock_generate.assert_awaited_once()
    assert result.overall_score == 0.78
    assert "large" in result.market_size_signal
    assert result.timing == "good — market ready for disruption"


@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.market_intelligence.service.get_session")
@pytest.mark.asyncio
async def test_get_signals_filters(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer
):
    """get_signals should filter by signal_type and min_relevance."""
    mock_signal = MagicMock()
    mock_signal.id = "sig-001"
    mock_signal.signal_type = "trend"
    mock_signal.title = "AI Growing"
    mock_signal.summary = "AI market expanding"
    mock_signal.relevance_score = 0.9
    mock_signal.impact_score = 0.8
    mock_signal.tags = ["ai"]
    mock_signal.detected_at = datetime(2024, 6, 1, tzinfo=UTC)
    mock_signal.venture_id = "ven-001"
    mock_signal.deleted_at = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_signal]
    mock_session.execute = AsyncMock(return_value=mock_result)

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    service = MarketIntelligence()
    results = await service.get_signals(
        "ven-001", signal_type="trend", min_relevance=0.5, limit=10
    )

    assert len(results) == 1
    assert results[0].signal_type == "trend"
