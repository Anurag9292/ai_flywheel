# ruff: noqa: E501
"""Customer Discovery Engine — validates problem spaces through structured interviews.

This module assists in the customer discovery process by:
1. Generating interview guides from hypotheses and assumptions
2. Analyzing transcripts to extract structured insights
3. Synthesizing findings across multiple interviews
4. Tracking assumption confidence over time
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.llm import generate
from ai_flywheel.core.traces import get_tracer

from .models import Assumption, DiscoveryProject, Interview
from .schemas import (
    AssumptionUpdate,
    DiscoveryProjectCreate,
    DiscoveryProjectResponse,
    InsightItem,
    InterviewGuideRequest,
    InterviewGuideResponse,
    SynthesisRequest,
    SynthesisResponse,
    TranscriptAnalysisRequest,
    TranscriptAnalysisResponse,
)

logger = structlog.get_logger()

MODULE_NAME = "customer_discovery"


class CustomerDiscoveryEngine:
    """Orchestrates the customer discovery workflow using LLM-powered analysis."""

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    # ------------------------------------------------------------------
    # Project CRUD
    # ------------------------------------------------------------------

    async def create_project(
        self, venture_id: str, data: DiscoveryProjectCreate
    ) -> DiscoveryProjectResponse:
        """Create a new discovery project and seed its assumptions."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "create_project"):
            async with get_session(venture_id) as session:
                project = DiscoveryProject(
                    venture_id=venture_id,
                    name=data.name,
                    domain=data.domain,
                    hypothesis=data.hypothesis,
                    assumptions=data.assumptions,
                    status="active",
                    interview_count=0,
                    confidence_score=0.0,
                )
                session.add(project)
                await session.flush()

                # Create individual assumption records for tracking
                for statement in data.assumptions:
                    assumption = Assumption(
                        venture_id=venture_id,
                        project_id=project.id,
                        statement=statement,
                        status="unvalidated",
                        evidence_for=[],
                        evidence_against=[],
                        confidence=0.0,
                    )
                    session.add(assumption)

                await session.flush()

                response = DiscoveryProjectResponse(
                    id=project.id,
                    venture_id=project.venture_id,
                    name=project.name,
                    domain=project.domain,
                    hypothesis=project.hypothesis,
                    assumptions=project.assumptions,
                    status=project.status,
                    interview_count=project.interview_count,
                    confidence_score=project.confidence_score,
                    created_at=project.created_at,
                )

            await self._event_bus.publish(
                event_type="discovery.project.created",
                source_module=MODULE_NAME,
                payload={"project_id": response.id, "domain": data.domain},
                venture_id=venture_id,
            )

            logger.info(
                "discovery_project_created",
                project_id=response.id,
                venture_id=venture_id,
                domain=data.domain,
                assumption_count=len(data.assumptions),
            )

            return response

    async def get_project(
        self, venture_id: str, project_id: str
    ) -> DiscoveryProjectResponse:
        """Retrieve a discovery project by ID."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            result = await session.execute(
                select(DiscoveryProject).where(
                    DiscoveryProject.id == project_id,
                    DiscoveryProject.venture_id == venture_id,
                    DiscoveryProject.deleted_at.is_(None),
                )
            )
            project = result.scalar_one()

            return DiscoveryProjectResponse(
                id=project.id,
                venture_id=project.venture_id,
                name=project.name,
                domain=project.domain,
                hypothesis=project.hypothesis,
                assumptions=project.assumptions,
                status=project.status,
                interview_count=project.interview_count,
                confidence_score=project.confidence_score,
                created_at=project.created_at,
            )

    async def list_projects(self, venture_id: str) -> list[DiscoveryProjectResponse]:
        """List all discovery projects for a venture."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            result = await session.execute(
                select(DiscoveryProject).where(
                    DiscoveryProject.venture_id == venture_id,
                    DiscoveryProject.deleted_at.is_(None),
                ).order_by(DiscoveryProject.created_at.desc())
            )
            projects = result.scalars().all()

            return [
                DiscoveryProjectResponse(
                    id=p.id,
                    venture_id=p.venture_id,
                    name=p.name,
                    domain=p.domain,
                    hypothesis=p.hypothesis,
                    assumptions=p.assumptions,
                    status=p.status,
                    interview_count=p.interview_count,
                    confidence_score=p.confidence_score,
                    created_at=p.created_at,
                )
                for p in projects
            ]

    # ------------------------------------------------------------------
    # Interview Guide Generation
    # ------------------------------------------------------------------

    async def generate_interview_guide(
        self, venture_id: str, request: InterviewGuideRequest
    ) -> InterviewGuideResponse:
        """Generate a tailored interview guide using LLM."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "generate_interview_guide",
            input_data={"project_id": request.project_id, "target_role": request.target_role},
        ) as span:
            # Fetch project context
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(DiscoveryProject).where(
                        DiscoveryProject.id == request.project_id,
                        DiscoveryProject.venture_id == venture_id,
                    )
                )
                project = result.scalar_one()

            # Build prompt
            focus_section = ""
            if request.focus_areas:
                focus_section = "\n\nFocus Areas to probe deeper:\n" + "\n".join(
                    f"- {area}" for area in request.focus_areas
                )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert customer discovery interviewer trained in "
                        "The Mom Test methodology. You create interview guides that elicit "
                        "honest, unbiased responses about real behaviors and pain points — "
                        "never leading questions or hypothetical scenarios.\n\n"
                        "Rules for great discovery questions:\n"
                        "1. Ask about specific past behaviors, not future intentions\n"
                        "2. Never mention your solution or hypothesis directly\n"
                        "3. Ask about the problem, not whether they'd use a solution\n"
                        "4. Dig into emotional weight — what's the cost of the status quo?\n"
                        "5. Use open-ended 'tell me about...' and 'walk me through...' phrasing\n"
                        "6. Include questions that can invalidate your assumptions\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Generate an interview guide for the following discovery project.\n\n"
                        f"Domain: {project.domain}\n"
                        f"Hypothesis: {project.hypothesis}\n"
                        f"Key Assumptions to Test:\n"
                        + "\n".join(f"  {i+1}. {a}" for i, a in enumerate(project.assumptions))
                        + f"\n\nTarget Interviewee Role: {request.target_role}"
                        + focus_section
                        + "\n\nRespond with JSON:\n"
                        "{\n"
                        '  "questions": ["<8-12 open-ended questions ordered from broad to specific>"],\n'
                        '  "opening_script": "<2-3 sentence warm intro that sets context without biasing>",\n'
                        '  "probing_tips": ["<5-7 follow-up probing techniques specific to this domain>"]\n'
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.7,
                venture_id=venture_id,
                module_name=MODULE_NAME,
                metadata={"project_id": request.project_id, "target_role": request.target_role},
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            # Parse LLM response
            parsed = _parse_json_response(llm_response.content)

            guide = InterviewGuideResponse(
                project_id=request.project_id,
                target_role=request.target_role,
                questions=parsed.get("questions", []),
                opening_script=parsed.get("opening_script", ""),
                probing_tips=parsed.get("probing_tips", []),
            )

            await self._event_bus.publish(
                event_type="discovery.guide.generated",
                source_module=MODULE_NAME,
                payload={
                    "project_id": request.project_id,
                    "target_role": request.target_role,
                    "question_count": len(guide.questions),
                },
                venture_id=venture_id,
            )

            logger.info(
                "interview_guide_generated",
                project_id=request.project_id,
                target_role=request.target_role,
                question_count=len(guide.questions),
            )

            return guide

    # ------------------------------------------------------------------
    # Transcript Analysis
    # ------------------------------------------------------------------

    async def analyze_transcript(
        self, venture_id: str, request: TranscriptAnalysisRequest
    ) -> TranscriptAnalysisResponse:
        """Analyze an interview transcript to extract insights and update assumptions."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "analyze_transcript",
            input_data={"project_id": request.project_id, "role": request.interviewee_role},
        ) as span:
            # Fetch project for context
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(DiscoveryProject).where(
                        DiscoveryProject.id == request.project_id,
                        DiscoveryProject.venture_id == venture_id,
                    )
                )
                project = result.scalar_one()

            # Build analysis prompt
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert customer discovery analyst. Your job is to extract "
                        "actionable insights from interview transcripts, identifying patterns "
                        "that validate or invalidate business assumptions.\n\n"
                        "For each insight, classify it into one of these categories:\n"
                        "- pain_point: A problem the interviewee actively experiences\n"
                        "- need: Something they explicitly need or want\n"
                        "- behavior: How they currently solve or cope with the problem\n"
                        "- motivation: What drives their decisions in this space\n"
                        "- workflow: Their current process or routine\n\n"
                        "For assumption updates, assess whether the transcript evidence "
                        "supports, contradicts, or is neutral toward each assumption. "
                        "Only include assumptions where there's meaningful signal.\n\n"
                        "For sentiment, assess the interviewee's overall emotional relationship "
                        "to the problem space: positive (excited about solutions), negative "
                        "(frustrated/in pain), mixed, or neutral.\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Analyze this interview transcript from the following discovery context.\n\n"
                        f"Domain: {project.domain}\n"
                        f"Hypothesis: {project.hypothesis}\n"
                        f"Assumptions to evaluate:\n"
                        + "\n".join(
                            f"  [{i}] {a}" for i, a in enumerate(project.assumptions)
                        )
                        + f"\n\nInterviewee Role: {request.interviewee_role}\n\n"
                        f"--- TRANSCRIPT ---\n{request.transcript}\n--- END TRANSCRIPT ---\n\n"
                        "Respond with JSON:\n"
                        "{\n"
                        '  "insights": [\n'
                        "    {\n"
                        '      "category": "<pain_point|need|behavior|motivation|workflow>",\n'
                        '      "finding": "<clear one-sentence insight>",\n'
                        '      "quote": "<exact or near-exact quote from transcript>",\n'
                        '      "confidence": <0.0-1.0>\n'
                        "    }\n"
                        "  ],\n"
                        '  "assumptions_updated": [\n'
                        "    {\n"
                        '      "assumption_index": <index from list above>,\n'
                        '      "direction": "<supports|contradicts|neutral>",\n'
                        '      "evidence": "<specific evidence from transcript>"\n'
                        "    }\n"
                        "  ],\n"
                        '  "sentiment": "<positive|negative|mixed|neutral>"\n'
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.3,
                venture_id=venture_id,
                module_name=MODULE_NAME,
                metadata={
                    "project_id": request.project_id,
                    "interviewee_role": request.interviewee_role,
                },
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            # Parse response
            parsed = _parse_json_response(llm_response.content)

            insights = [
                InsightItem(**item) for item in parsed.get("insights", [])
            ]
            assumptions_updated = [
                AssumptionUpdate(**item)
                for item in parsed.get("assumptions_updated", [])
            ]
            sentiment = parsed.get("sentiment", "neutral")

            # Persist interview and update project state
            async with get_session(venture_id) as session:
                interview = Interview(
                    venture_id=venture_id,
                    project_id=request.project_id,
                    interviewee_role=request.interviewee_role,
                    transcript=request.transcript,
                    extracted_insights=[i.model_dump() for i in insights],
                    sentiment=sentiment,
                    recorded_at=datetime.now(UTC),
                )
                session.add(interview)
                await session.flush()

                interview_id = interview.id

                # Update project interview count
                proj_result = await session.execute(
                    select(DiscoveryProject).where(
                        DiscoveryProject.id == request.project_id
                    )
                )
                proj = proj_result.scalar_one()
                proj.interview_count += 1

                # Update assumption records with new evidence
                await self._update_assumptions(
                    session, request.project_id, assumptions_updated
                )

            response = TranscriptAnalysisResponse(
                interview_id=interview_id,
                insights=insights,
                assumptions_updated=assumptions_updated,
                sentiment=sentiment,
            )

            await self._event_bus.publish(
                event_type="discovery.transcript.analyzed",
                source_module=MODULE_NAME,
                payload={
                    "project_id": request.project_id,
                    "interview_id": interview_id,
                    "insight_count": len(insights),
                    "sentiment": sentiment,
                },
                venture_id=venture_id,
            )

            logger.info(
                "transcript_analyzed",
                project_id=request.project_id,
                interview_id=interview_id,
                insight_count=len(insights),
                assumptions_touched=len(assumptions_updated),
                sentiment=sentiment,
            )

            return response

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    async def synthesize(
        self, venture_id: str, request: SynthesisRequest
    ) -> SynthesisResponse:
        """Synthesize findings across all interviews in a project."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "synthesize",
            input_data={"project_id": request.project_id},
        ) as span:
            # Fetch project with all interviews and assumptions
            async with get_session(venture_id) as session:
                proj_result = await session.execute(
                    select(DiscoveryProject).where(
                        DiscoveryProject.id == request.project_id,
                        DiscoveryProject.venture_id == venture_id,
                    )
                )
                project = proj_result.scalar_one()

                interview_result = await session.execute(
                    select(Interview).where(
                        Interview.project_id == request.project_id,
                        Interview.venture_id == venture_id,
                        Interview.deleted_at.is_(None),
                    ).order_by(Interview.recorded_at)
                )
                interviews = interview_result.scalars().all()

                assumption_result = await session.execute(
                    select(Assumption).where(
                        Assumption.project_id == request.project_id,
                        Assumption.venture_id == venture_id,
                    )
                )
                assumptions = assumption_result.scalars().all()

            # Prepare interview summaries for the LLM
            interview_summaries = []
            for interview in interviews:
                interview_summaries.append({
                    "role": interview.interviewee_role,
                    "sentiment": interview.sentiment,
                    "insights": interview.extracted_insights,
                })

            assumption_summaries = []
            for a in assumptions:
                assumption_summaries.append({
                    "statement": a.statement,
                    "status": a.status,
                    "evidence_for_count": len(a.evidence_for),
                    "evidence_against_count": len(a.evidence_against),
                    "confidence": a.confidence,
                })

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a strategic customer discovery analyst synthesizing findings "
                        "across multiple interviews. Your job is to identify patterns, validate "
                        "or invalidate the original hypothesis, and recommend concrete next steps.\n\n"
                        "Focus on:\n"
                        "1. Patterns that appear across multiple interviews (not just one)\n"
                        "2. Surprising findings that challenge the initial hypothesis\n"
                        "3. Clear signals vs noise — weight repeated themes heavily\n"
                        "4. Actionable recommendations: pivot, persevere, or investigate further\n"
                        "5. Honest assessment of overall confidence in the hypothesis\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Synthesize the findings from {len(interviews)} interviews.\n\n"
                        f"Domain: {project.domain}\n"
                        f"Original Hypothesis: {project.hypothesis}\n\n"
                        f"Assumption Status:\n"
                        + json.dumps(assumption_summaries, indent=2)
                        + "\n\nInterview Data:\n"
                        + json.dumps(interview_summaries, indent=2)
                        + "\n\nRespond with JSON:\n"
                        "{\n"
                        '  "patterns": ["<recurring themes across 2+ interviews>"],\n'
                        '  "key_findings": ["<top 3-5 most important validated findings>"],\n'
                        '  "recommendations": ["<actionable next steps: pivot/persevere/dig deeper>"],\n'
                        '  "overall_confidence": <0.0-1.0 confidence in the original hypothesis>,\n'
                        '  "assumption_status": [\n'
                        "    {\n"
                        '      "statement": "<assumption text>",\n'
                        '      "status": "<validated|invalidated|uncertain|unvalidated>",\n'
                        '      "confidence": <0.0-1.0>,\n'
                        '      "summary": "<one-line evidence summary>"\n'
                        "    }\n"
                        "  ]\n"
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.4,
                venture_id=venture_id,
                module_name=MODULE_NAME,
                metadata={"project_id": request.project_id},
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            overall_confidence = parsed.get("overall_confidence", 0.0)

            # Update project confidence score
            async with get_session(venture_id) as session:
                proj_result = await session.execute(
                    select(DiscoveryProject).where(
                        DiscoveryProject.id == request.project_id
                    )
                )
                proj = proj_result.scalar_one()
                proj.confidence_score = overall_confidence

            response = SynthesisResponse(
                project_id=request.project_id,
                patterns=parsed.get("patterns", []),
                key_findings=parsed.get("key_findings", []),
                recommendations=parsed.get("recommendations", []),
                overall_confidence=overall_confidence,
                assumption_status=parsed.get("assumption_status", []),
            )

            await self._event_bus.publish(
                event_type="discovery.synthesized",
                source_module=MODULE_NAME,
                payload={
                    "project_id": request.project_id,
                    "overall_confidence": overall_confidence,
                    "pattern_count": len(response.patterns),
                    "interview_count": len(interviews),
                },
                venture_id=venture_id,
            )

            logger.info(
                "discovery_synthesized",
                project_id=request.project_id,
                interview_count=len(interviews),
                overall_confidence=overall_confidence,
                pattern_count=len(response.patterns),
            )

            return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _update_assumptions(
        self,
        session: Any,
        project_id: str,
        updates: list[AssumptionUpdate],
    ) -> None:
        """Update assumption records based on transcript analysis."""
        if not updates:
            return

        result = await session.execute(
            select(Assumption).where(
                Assumption.project_id == project_id
            ).order_by(Assumption.created_at)
        )
        assumptions = list(result.scalars().all())

        for update in updates:
            if update.assumption_index >= len(assumptions):
                continue

            assumption = assumptions[update.assumption_index]

            if update.direction == "supports":
                evidence_for = list(assumption.evidence_for)
                evidence_for.append(update.evidence)
                assumption.evidence_for = evidence_for
            elif update.direction == "contradicts":
                evidence_against = list(assumption.evidence_against)
                evidence_against.append(update.evidence)
                assumption.evidence_against = evidence_against

            # Recalculate confidence and status
            total_evidence = len(assumption.evidence_for) + len(assumption.evidence_against)
            if total_evidence > 0:
                support_ratio = len(assumption.evidence_for) / total_evidence
                assumption.confidence = min(total_evidence / 5.0, 1.0)  # Caps at 5 data points

                if assumption.confidence >= 0.6:
                    if support_ratio >= 0.7:
                        assumption.status = "validated"
                    elif support_ratio <= 0.3:
                        assumption.status = "invalidated"
                    else:
                        assumption.status = "uncertain"


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(
            "json_parse_failed",
            error=str(e),
            content_preview=text[:200],
        )
        # Return empty structure rather than crash
        return {}
