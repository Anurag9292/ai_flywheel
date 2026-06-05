"""Unit tests for CustomerDiscoveryEngine service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.core.contracts.schemas import LLMResponse
from ai_flywheel.modules.product_intelligence.customer_discovery.schemas import (
    DiscoveryProjectCreate,
    InterviewGuideRequest,
    SynthesisRequest,
    TranscriptAnalysisRequest,
)
from ai_flywheel.modules.product_intelligence.customer_discovery.service import (
    CustomerDiscoveryEngine,
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
    tracer.start_trace.return_value = "trace-001"

    mock_span = MagicMock()
    mock_span.set_cost = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    tracer.span.return_value = span_cm

    return tracer


@pytest.fixture
def fake_project():
    """Create a fake DiscoveryProject ORM object."""
    project = MagicMock()
    project.id = "proj-001"
    project.venture_id = "ven-001"
    project.name = "Test Discovery"
    project.domain = "AI Education"
    project.hypothesis = "Teachers need AI tools to personalize learning"
    project.assumptions = [
        "Teachers spend >2h/day on lesson planning",
        "Personalization improves student outcomes",
        "Teachers are willing to adopt new tech tools",
    ]
    project.status = "active"
    project.interview_count = 0
    project.confidence_score = 0.0
    project.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    project.deleted_at = None
    return project


@pytest.fixture
def fake_interview():
    """Create a fake Interview ORM object."""
    interview = MagicMock()
    interview.id = "int-001"
    interview.venture_id = "ven-001"
    interview.project_id = "proj-001"
    interview.interviewee_role = "High School Teacher"
    interview.transcript = "Sample transcript..."
    interview.extracted_insights = [
        {
            "category": "pain_point",
            "finding": "Spends 3 hours on planning",
            "quote": "I spend about 3 hours every evening planning",
            "confidence": 0.9,
        }
    ]
    interview.sentiment = "negative"
    interview.recorded_at = datetime(2024, 2, 1, tzinfo=UTC)
    return interview


@pytest.fixture
def fake_assumption():
    """Create a fake Assumption ORM object."""
    assumption = MagicMock()
    assumption.id = "asmp-001"
    assumption.project_id = "proj-001"
    assumption.statement = "Teachers spend >2h/day on lesson planning"
    assumption.status = "unvalidated"
    assumption.evidence_for = []
    assumption.evidence_against = []
    assumption.confidence = 0.0
    assumption.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return assumption


@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_session")
async def test_create_project_stores_project(
    mock_get_session, mock_get_event_bus, mock_get_tracer,
    mock_session, mock_event_bus, mock_tracer, fake_project
):
    """create_project should persist project and assumptions, emit event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Simulate DB default assignment on flush: set id and created_at on added objects
    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    mock_session.add.side_effect = add_side_effect

    flush_count = [0]

    async def flush_side_effect():
        flush_count[0] += 1
        for obj in added_objects:
            if not hasattr(obj, 'id') or obj.id is None:
                obj.id = f"generated-{flush_count[0]}-{id(obj)}"
            if hasattr(obj, 'created_at') and obj.created_at is None:
                obj.created_at = datetime(2024, 1, 1, tzinfo=UTC)

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    engine = CustomerDiscoveryEngine()
    data = DiscoveryProjectCreate(
        name="Test Discovery",
        domain="AI Education",
        hypothesis="Teachers need AI tools to personalize learning",
        assumptions=[
            "Teachers spend >2h/day on lesson planning",
            "Personalization improves student outcomes",
        ],
    )
    result = await engine.create_project("ven-001", data)

    # Project + 2 assumptions = 3 add calls
    assert mock_session.add.call_count == 3
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "discovery.project.created"
    assert publish_kwargs["venture_id"] == "ven-001"


@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.generate")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_session")
async def test_generate_interview_guide_calls_llm(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_project
):
    """generate_interview_guide should call LLM and return structured questions."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Mock the DB query returning the project
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_project
    mock_session.execute.return_value = mock_result

    # Mock LLM response with JSON content
    guide_json = json.dumps({
        "questions": [
            "Tell me about your typical lesson planning process.",
            "Walk me through how you adapt lessons for different students.",
            "What's the most frustrating part of your daily workflow?",
        ],
        "opening_script": "Thanks for taking time to chat. I'd love to learn about your teaching experience.",
        "probing_tips": [
            "Ask for specific examples",
            "Dig into emotional responses",
        ],
    })
    mock_generate.return_value = LLMResponse(
        content=guide_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=200,
        tokens_output=150,
        cost_usd=0.002,
    )

    engine = CustomerDiscoveryEngine()
    request = InterviewGuideRequest(
        project_id="proj-001",
        target_role="High School Teacher",
    )
    result = await engine.generate_interview_guide("ven-001", request)

    mock_generate.assert_awaited_once()
    assert len(result.questions) == 3
    assert result.target_role == "High School Teacher"
    assert result.project_id == "proj-001"
    assert "lesson planning" in result.questions[0]
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "discovery.guide.generated"


@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.generate")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_session")
async def test_analyze_transcript_extracts_insights(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_project
):
    """analyze_transcript should extract insights from the transcript via LLM."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Track added objects to simulate DB defaults on flush
    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    mock_session.add.side_effect = add_side_effect

    async def flush_side_effect():
        for obj in added_objects:
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = "int-generated-001"

    mock_session.flush = AsyncMock(side_effect=flush_side_effect)

    # Mock execute to return fake_project for all DB queries
    def execute_side_effect(*args, **kwargs):
        result = MagicMock()
        result.scalar_one.return_value = fake_project
        result.scalar_one_or_none.return_value = fake_project
        result.scalars.return_value.all.return_value = []
        return result

    mock_session.execute.side_effect = execute_side_effect

    # Mock LLM to return analysis JSON
    analysis_json = json.dumps({
        "insights": [
            {
                "category": "pain_point",
                "finding": "Teacher spends 3+ hours daily on planning",
                "quote": "I spend about 3 hours every evening just planning tomorrow's lessons",
                "confidence": 0.9,
            },
            {
                "category": "behavior",
                "finding": "Uses printed worksheets rather than digital tools",
                "quote": "I mostly print out worksheets, it's just easier",
                "confidence": 0.7,
            },
        ],
        "assumptions_updated": [
            {
                "assumption_index": 0,
                "direction": "supports",
                "evidence": "Teacher confirmed 3+ hours daily on planning",
            }
        ],
        "sentiment": "negative",
    })
    mock_generate.return_value = LLMResponse(
        content=analysis_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=500,
        tokens_output=300,
        cost_usd=0.005,
    )

    engine = CustomerDiscoveryEngine()
    request = TranscriptAnalysisRequest(
        project_id="proj-001",
        interviewee_role="High School Teacher",
        transcript="Interviewer: Tell me about your planning process...\nTeacher: I spend about 3 hours every evening just planning tomorrow's lessons...",
    )
    result = await engine.analyze_transcript("ven-001", request)

    mock_generate.assert_awaited_once()
    assert len(result.insights) == 2
    assert result.insights[0].category == "pain_point"
    assert result.sentiment == "negative"
    assert len(result.assumptions_updated) == 1
    assert result.assumptions_updated[0].direction == "supports"


@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.generate")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_session")
async def test_synthesize_aggregates_interviews(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_project, fake_interview, fake_assumption
):
    """synthesize should aggregate findings across interviews via LLM."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    # Mock DB queries: project, interviews, assumptions, then project update
    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Project query
            result.scalar_one.return_value = fake_project
        elif call_count[0] == 2:
            # Interviews query
            result.scalars.return_value.all.return_value = [fake_interview]
        elif call_count[0] == 3:
            # Assumptions query
            result.scalars.return_value.all.return_value = [fake_assumption]
        else:
            # Project update query
            result.scalar_one.return_value = fake_project
        return result

    mock_session.execute.side_effect = execute_side_effect

    synthesis_json = json.dumps({
        "patterns": [
            "Teachers consistently report 2-4 hours on daily planning",
            "Strong preference for familiar tools over new digital solutions",
        ],
        "key_findings": [
            "Time spent on planning validated across multiple interviews",
            "Tech adoption barrier is higher than expected",
        ],
        "recommendations": [
            "Pivot to augmenting existing workflows rather than replacing them",
            "Focus on time-saving as the primary value proposition",
        ],
        "overall_confidence": 0.72,
        "assumption_status": [
            {
                "statement": "Teachers spend >2h/day on lesson planning",
                "status": "validated",
                "confidence": 0.9,
                "summary": "Confirmed by all interviewees",
            }
        ],
    })
    mock_generate.return_value = LLMResponse(
        content=synthesis_json,
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=800,
        tokens_output=400,
        cost_usd=0.008,
    )

    engine = CustomerDiscoveryEngine()
    request = SynthesisRequest(project_id="proj-001")
    result = await engine.synthesize("ven-001", request)

    mock_generate.assert_awaited_once()
    assert result.project_id == "proj-001"
    assert len(result.patterns) == 2
    assert len(result.key_findings) == 2
    assert len(result.recommendations) == 2
    assert result.overall_confidence == 0.72
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "discovery.synthesized"


@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.generate")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_tracer")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_event_bus")
@patch("ai_flywheel.modules.product_intelligence.customer_discovery.service.get_session")
async def test_generate_interview_guide_handles_malformed_json(
    mock_get_session, mock_get_event_bus, mock_get_tracer, mock_generate,
    mock_session, mock_event_bus, mock_tracer, fake_project
):
    """generate_interview_guide should handle LLM returning invalid JSON gracefully."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus
    mock_get_tracer.return_value = mock_tracer

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = fake_project
    mock_session.execute.return_value = mock_result

    # LLM returns invalid/empty JSON
    mock_generate.return_value = LLMResponse(
        content="I'm sorry, I cannot generate that.",
        model="gpt-4o-mini",
        provider="openai",
        tokens_input=100,
        tokens_output=20,
        cost_usd=0.001,
    )

    engine = CustomerDiscoveryEngine()
    request = InterviewGuideRequest(
        project_id="proj-001",
        target_role="High School Teacher",
    )
    # Should not raise, but return empty lists (graceful degradation)
    result = await engine.generate_interview_guide("ven-001", request)

    assert result.questions == []
    assert result.opening_script == ""
    assert result.probing_tips == []
