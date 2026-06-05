"""Unit tests for ProductExperienceEngine service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.modules.product_intelligence.product_experience.schemas import (
    AIInteractionRequest,
    FeaturePrioritizationRequest,
    ProductSpecCreate,
    ScreenArchitectureRequest,
)
from ai_flywheel.modules.product_intelligence.product_experience.service import (
    ProductExperienceEngine,
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
def fake_product_spec():
    """Create a fake ProductSpec ORM object."""
    spec = MagicMock()
    spec.id = "prod-001"
    spec.venture_id = "ven-001"
    spec.name = "AI Tutor Platform"
    spec.description = "An AI-powered tutoring platform"
    spec.personas = [{"name": "Teacher", "goals": [], "pain_points": [], "context": ""}]
    spec.features = [{"name": "Lesson Generation", "priority": "medium"}]
    spec.ai_interaction_patterns = []
    spec.screen_architecture = None
    spec.ux_flows = []
    spec.status = "draft"
    spec.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    spec.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    spec.deleted_at = None
    return spec


@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_session")
async def test_create_product_spec(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_product_spec,
):
    """create_product_spec should persist spec with seeded personas and features."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Simulate flush assigning ID
    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    mock_session.add.side_effect = add_side_effect

    async def flush_side_effect():
        for obj in added_objects:
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = "prod-001"
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)
            if hasattr(obj, "updated_at") and obj.updated_at is None:
                obj.updated_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    engine = ProductExperienceEngine()
    data = ProductSpecCreate(
        name="AI Tutor Platform",
        description="An AI-powered tutoring platform",
        target_personas=["Teacher", "Student"],
        core_capabilities=["Lesson Generation", "Progress Tracking"],
    )
    result = await engine.create_product_spec("ven-001", data)

    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "product.spec.created"
    assert publish_kwargs["venture_id"] == "ven-001"


@patch("ai_flywheel.modules.product_intelligence.product_experience.service.generate")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_session")
async def test_prioritize_features_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_product_spec,
):
    """prioritize_features should call LLM and return scored features."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_product_spec
    mock_session.execute.return_value = mock_result

    prioritization_data = {
        "prioritized_features": [
            {"name": "Lesson Generation", "impact": 9, "effort": 5, "risk": 3, "ai_leverage": 9, "priority_score": 7.6, "priority": "critical", "recommendation": "Build first"},
            {"name": "Progress Tracking", "impact": 7, "effort": 4, "risk": 2, "ai_leverage": 6, "priority_score": 5.8, "priority": "high", "recommendation": "Build second"},
        ],
        "rationale": "Focus on AI-heavy features first for maximum leverage.",
    }
    mock_generate.return_value = LLMResponse(
        content=json.dumps(prioritization_data),
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=200,
        tokens_output=400,
        cost_usd=0.003,
    )

    engine = ProductExperienceEngine()
    request = FeaturePrioritizationRequest(
        product_id="prod-001",
        features=[{"name": "Lesson Generation"}, {"name": "Progress Tracking"}],
        north_star_metric="weekly active teachers",
    )
    result = await engine.prioritize_features("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.product_id == "prod-001"
    assert len(result.prioritized_features) == 2
    assert result.prioritized_features[0]["priority"] == "critical"
    assert result.rationale == "Focus on AI-heavy features first for maximum leverage."


@patch("ai_flywheel.modules.product_intelligence.product_experience.service.generate")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_session")
async def test_recommend_ai_patterns(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_product_spec,
):
    """recommend_ai_patterns should return pattern per capability."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_product_spec
    mock_session.execute.return_value = mock_result

    patterns_data = {
        "patterns": [
            {"capability": "Lesson Generation", "recommended_pattern": "copilot", "autonomy_level": 3, "rationale": "Teachers review AI-drafted lessons"},
            {"capability": "Grading", "recommended_pattern": "queue", "autonomy_level": 4, "rationale": "AI grades async, teacher reviews exceptions"},
        ]
    }
    mock_generate.return_value = LLMResponse(
        content=json.dumps(patterns_data),
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=180,
        tokens_output=350,
        cost_usd=0.002,
    )

    engine = ProductExperienceEngine()
    request = AIInteractionRequest(
        product_id="prod-001",
        capabilities=["Lesson Generation", "Grading"],
    )
    result = await engine.recommend_ai_patterns("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.product_id == "prod-001"
    assert len(result.patterns) == 2
    assert result.patterns[0]["recommended_pattern"] == "copilot"
    assert result.patterns[1]["recommended_pattern"] == "queue"


@patch("ai_flywheel.modules.product_intelligence.product_experience.service.generate")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.product_experience.service.get_session")
async def test_generate_screen_architecture(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_product_spec,
):
    """generate_screen_architecture should return screens, nav, and hierarchy."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_product_spec
    mock_session.execute.return_value = mock_result

    arch_data = {
        "screens": [
            {"id": "dashboard", "name": "Dashboard", "purpose": "Overview", "primary_actions": ["view stats"], "ai_features": ["insights"], "components": ["chart"]},
            {"id": "lessons", "name": "Lessons", "purpose": "Manage lessons", "primary_actions": ["create"], "ai_features": ["auto-generate"], "components": ["list"]},
        ],
        "navigation": {"type": "sidebar", "primary_items": ["Dashboard", "Lessons"], "secondary_items": ["Settings"]},
        "information_hierarchy": ["Active lessons", "Student progress", "AI suggestions"],
    }
    mock_generate.return_value = LLMResponse(
        content=json.dumps(arch_data),
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=250,
        tokens_output=500,
        cost_usd=0.004,
    )

    engine = ProductExperienceEngine()
    request = ScreenArchitectureRequest(
        product_id="prod-001",
        user_goals=["Plan lessons quickly", "Track student progress"],
    )
    result = await engine.generate_screen_architecture("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.product_id == "prod-001"
    assert len(result.screens) == 2
    assert result.navigation["type"] == "sidebar"
    assert len(result.information_hierarchy) == 3
