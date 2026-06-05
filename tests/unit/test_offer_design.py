"""Unit tests for OfferDesignEngine service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.modules.product_intelligence.offer_design.schemas import (
    ICPRequest,
    LandingCopyRequest,
    OfferCreate,
    PositioningRequest,
    PricingRequest,
)
from ai_flywheel.modules.product_intelligence.offer_design.service import (
    OfferDesignEngine,
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
    mock_span.output_data = None
    mock_span.metadata = {}
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm

    return tracer


@pytest.fixture
def fake_offer():
    """Create a fake Offer ORM object."""
    offer = MagicMock()
    offer.id = "offer-001"
    offer.venture_id = "ven-001"
    offer.name = "AI Tutor Pro"
    offer.status = "draft"
    offer.icp = None
    offer.positioning = None
    offer.pricing = None
    offer.messaging = None
    offer.objection_rebuttals = None
    offer.version = 1
    offer.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    offer.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    offer.deleted_at = None
    return offer


@patch("ai_flywheel.modules.product_intelligence.offer_design.service.generate")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_session")
async def test_create_offer_stores_and_emits_event(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_offer,
):
    """create_offer should persist an offer and emit offer.created event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # flush assigns ID
    async def flush_side_effect():
        for call_args in mock_session.add.call_args_list:
            obj = call_args[0][0]
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = "offer-001"
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    # Mock DB select returning the offer
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_offer
    mock_session.execute.return_value = mock_result

    # Mock LLM for ICP and positioning
    icp_json = json.dumps({"behavioral": {}, "firmographic": {}, "psychographic": {}, "summary": "Test ICP"})
    positioning_json = json.dumps({"category": "EdTech", "value_proposition": "AI tutoring"})
    mock_generate.return_value = LLMResponse(
        content=icp_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=100,
        tokens_output=200,
        cost_usd=0.001,
    )

    engine = OfferDesignEngine()
    data = OfferCreate(
        name="AI Tutor Pro",
        domain="Education",
        target_audience="K-12 Teachers",
        problem_statement="Lesson planning is tedious",
        solution_description="AI-generated personalized lessons",
    )
    result = await engine.create_offer("ven-001", data)

    # Verify stored
    mock_session.add.assert_called()
    # Verify event published (multiple events: offer.created, offer.icp.generated, etc.)
    assert mock_event_bus.publish.call_count >= 1
    # Find the offer.created event
    offer_created_calls = [
        c for c in mock_event_bus.publish.call_args_list
        if c[1].get("event_type") == "offer.created"
    ]
    assert len(offer_created_calls) == 1
    assert offer_created_calls[0][1]["venture_id"] == "ven-001"


@patch("ai_flywheel.modules.product_intelligence.offer_design.service.generate")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_session")
async def test_generate_icp_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_offer,
):
    """generate_icp should call LLM and return structured ICP data."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_offer
    mock_session.execute.return_value = mock_result

    icp_data = {
        "behavioral": {"buying_triggers": ["pain point"]},
        "firmographic": {"company_size": "50-200"},
        "psychographic": {"values": ["efficiency"]},
        "summary": "Tech-savvy educators",
    }
    mock_generate.return_value = LLMResponse(
        content=json.dumps(icp_data),
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=150,
        tokens_output=300,
        cost_usd=0.002,
    )

    engine = OfferDesignEngine()
    request = ICPRequest(
        offer_id="offer-001",
        domain="Education",
        initial_description="Teachers who need AI tools",
    )
    result = await engine.generate_icp("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.offer_id == "offer-001"
    assert result.icp["summary"] == "Tech-savvy educators"


@patch("ai_flywheel.modules.product_intelligence.offer_design.service.generate")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_session")
async def test_generate_positioning_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_offer,
):
    """generate_positioning should call LLM and persist positioning."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_offer
    mock_session.execute.return_value = mock_result

    positioning_data = {
        "category": "AI-powered EdTech",
        "value_proposition": "Personalized lessons in seconds",
        "competitive_frame": {"key_differentiators": ["speed", "accuracy"]},
        "positioning_statement": "For teachers who...",
        "messaging_pillars": ["Speed", "Quality", "Ease"],
        "proof_points": ["95% satisfaction"],
    }
    mock_generate.return_value = LLMResponse(
        content=json.dumps(positioning_data),
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=200,
        tokens_output=400,
        cost_usd=0.003,
    )

    engine = OfferDesignEngine()
    request = PositioningRequest(
        offer_id="offer-001",
        domain="Education",
        competitors=["Competitor A"],
        differentiators=["AI-native"],
    )
    result = await engine.generate_positioning("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.offer_id == "offer-001"
    assert result.positioning["category"] == "AI-powered EdTech"


@patch("ai_flywheel.modules.product_intelligence.offer_design.service.generate")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_session")
async def test_generate_pricing_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_offer,
):
    """generate_pricing should call LLM and return pricing tiers."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_offer
    mock_session.execute.return_value = mock_result

    pricing_data = {
        "model": "tiered",
        "rationale": "Value-based pricing fits EdTech",
        "tiers": [
            {"name": "Starter", "price": "$29/mo", "target_user": "Individual teacher"},
            {"name": "Pro", "price": "$99/mo", "target_user": "Department"},
        ],
        "price_points": {"anchor_price": "$199", "recommended_price": "$99", "entry_price": "$29"},
        "value_metrics": ["lessons generated", "students reached"],
        "psychological_triggers": ["free trial", "money-back guarantee"],
        "discount_strategy": "Annual discount 20%",
    }
    mock_generate.return_value = LLMResponse(
        content=json.dumps(pricing_data),
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=250,
        tokens_output=500,
        cost_usd=0.004,
    )

    engine = OfferDesignEngine()
    request = PricingRequest(
        offer_id="offer-001",
        value_delivered="Automated lesson planning",
        target_segment="K-12 teachers",
    )
    result = await engine.generate_pricing("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.offer_id == "offer-001"
    assert result.pricing["model"] == "tiered"
    assert len(result.pricing["tiers"]) == 2


@patch("ai_flywheel.modules.product_intelligence.offer_design.service.generate")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.offer_design.service.get_session")
async def test_generate_landing_copy(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_offer,
):
    """generate_landing_copy should call LLM and return full copy structure."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_offer
    mock_session.execute.return_value = mock_result

    copy_data = {
        "headline": "Teach Smarter, Not Harder",
        "subheadline": "AI-powered lesson planning in seconds",
        "hero_body": "Stop spending hours on lesson prep.",
        "benefits": ["Save 3 hours daily", "Personalized for every student"],
        "social_proof_frame": "Join 5,000+ teachers",
        "cta_primary": "Start Free Trial",
        "cta_secondary": "Watch Demo",
        "full_page_structure": [
            {"section": "hero", "purpose": "hook", "content": "Main message"}
        ],
    }
    mock_generate.return_value = LLMResponse(
        content=json.dumps(copy_data),
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=300,
        tokens_output=600,
        cost_usd=0.005,
    )

    engine = OfferDesignEngine()
    request = LandingCopyRequest(
        offer_id="offer-001",
        persona="K-12 Teacher",
        tone="professional",
    )
    result = await engine.generate_landing_copy("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.offer_id == "offer-001"
    assert result.headline == "Teach Smarter, Not Harder"
    assert result.cta_primary == "Start Free Trial"
    assert len(result.benefits) == 2
