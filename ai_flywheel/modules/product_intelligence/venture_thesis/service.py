# ruff: noqa: E501
"""Venture Thesis Engine — validates venture hypotheses through structured evidence.

This module manages the thesis validation lifecycle:
1. Creating structured theses with testable assumptions
2. Collecting and weighting evidence (supports/contradicts/neutral)
3. Bayesian-inspired confidence updating on assumptions and thesis
4. LLM-powered validation plan generation and venture memo writing
5. Kill signal monitoring for thesis invalidation
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

from .models import EvidenceItem, Thesis, ThesisAssumption
from .schemas import (
    AddEvidenceRequest,
    AssumptionResponse,
    EvidenceResponse,
    ThesisCreate,
    ThesisMemoRequest,
    ThesisMemoResponse,
    ThesisResponse,
    ValidationPlanRequest,
    ValidationPlanResponse,
    ValidationStep,
)

logger = structlog.get_logger()

MODULE_NAME = "venture_thesis"


class VentureThesisEngine:
    """Orchestrates venture thesis validation through evidence-based reasoning."""

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    # ------------------------------------------------------------------
    # Thesis CRUD
    # ------------------------------------------------------------------

    async def create_thesis(
        self, venture_id: str, data: ThesisCreate
    ) -> ThesisResponse:
        """Create a new venture thesis with its underlying assumptions."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "create_thesis"):
            async with get_session(venture_id) as session:
                thesis = Thesis(
                    venture_id=venture_id,
                    title=data.title,
                    hypothesis=data.hypothesis,
                    status="active",
                    confidence=0.5,
                    evidence_count=0,
                    assumptions=[a.statement for a in data.assumptions],
                    kill_signals=data.kill_signals,
                    validation_plan=None,
                )
                session.add(thesis)
                await session.flush()

                # Create individual assumption records
                assumption_models: list[ThesisAssumption] = []
                for assumption_data in data.assumptions:
                    assumption = ThesisAssumption(
                        venture_id=venture_id,
                        thesis_id=thesis.id,
                        statement=assumption_data.statement,
                        risk_level=assumption_data.risk_level,
                        status="untested",
                        confidence=0.5,
                        evidence=[],
                        validation_method=assumption_data.validation_method,
                        experiment_ids=[],
                    )
                    session.add(assumption)
                    assumption_models.append(assumption)

                await session.flush()

                response = self._build_thesis_response(thesis, assumption_models)

            await self._event_bus.publish(
                event_type="thesis.created",
                source_module=MODULE_NAME,
                payload={
                    "thesis_id": response.id,
                    "title": data.title,
                    "assumption_count": len(data.assumptions),
                    "kill_signal_count": len(data.kill_signals),
                },
                venture_id=venture_id,
            )

            logger.info(
                "thesis_created",
                thesis_id=response.id,
                venture_id=venture_id,
                title=data.title,
                assumption_count=len(data.assumptions),
            )

            return response

    async def get_thesis(self, venture_id: str, thesis_id: str) -> ThesisResponse:
        """Retrieve a thesis by ID with its assumptions."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Thesis).where(
                    Thesis.id == thesis_id,
                    Thesis.venture_id == venture_id,
                    Thesis.deleted_at.is_(None),
                )
            )
            thesis = result.scalar_one()

            assumptions_result = await session.execute(
                select(ThesisAssumption).where(
                    ThesisAssumption.thesis_id == thesis_id,
                    ThesisAssumption.venture_id == venture_id,
                    ThesisAssumption.deleted_at.is_(None),
                ).order_by(ThesisAssumption.created_at)
            )
            assumptions = list(assumptions_result.scalars().all())

            return self._build_thesis_response(thesis, assumptions)

    async def list_theses(
        self, venture_id: str, status: str | None = None
    ) -> list[ThesisResponse]:
        """List all theses for a venture, optionally filtered by status."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            query = select(Thesis).where(
                Thesis.venture_id == venture_id,
                Thesis.deleted_at.is_(None),
            )
            if status:
                query = query.where(Thesis.status == status)
            query = query.order_by(Thesis.created_at.desc())

            result = await session.execute(query)
            theses = result.scalars().all()

            responses = []
            for thesis in theses:
                assumptions_result = await session.execute(
                    select(ThesisAssumption).where(
                        ThesisAssumption.thesis_id == thesis.id,
                        ThesisAssumption.venture_id == venture_id,
                        ThesisAssumption.deleted_at.is_(None),
                    ).order_by(ThesisAssumption.created_at)
                )
                assumptions = list(assumptions_result.scalars().all())
                responses.append(self._build_thesis_response(thesis, assumptions))

            return responses

    async def update_thesis_status(
        self, venture_id: str, thesis_id: str, status: str
    ) -> ThesisResponse:
        """Update a thesis status (active, validated, invalidated, pivoted)."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "update_thesis_status"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(Thesis).where(
                        Thesis.id == thesis_id,
                        Thesis.venture_id == venture_id,
                        Thesis.deleted_at.is_(None),
                    )
                )
                thesis = result.scalar_one()
                old_status = thesis.status
                thesis.status = status

                assumptions_result = await session.execute(
                    select(ThesisAssumption).where(
                        ThesisAssumption.thesis_id == thesis_id,
                        ThesisAssumption.venture_id == venture_id,
                        ThesisAssumption.deleted_at.is_(None),
                    ).order_by(ThesisAssumption.created_at)
                )
                assumptions = list(assumptions_result.scalars().all())

                response = self._build_thesis_response(thesis, assumptions)

            await self._event_bus.publish(
                event_type="thesis.status.changed",
                source_module=MODULE_NAME,
                payload={
                    "thesis_id": thesis_id,
                    "old_status": old_status,
                    "new_status": status,
                },
                venture_id=venture_id,
            )

            logger.info(
                "thesis_status_changed",
                thesis_id=thesis_id,
                venture_id=venture_id,
                old_status=old_status,
                new_status=status,
            )

            return response

    # ------------------------------------------------------------------
    # Evidence Management
    # ------------------------------------------------------------------

    async def add_evidence(
        self, venture_id: str, request: AddEvidenceRequest
    ) -> EvidenceResponse:
        """Add evidence to a thesis/assumption and update confidence scores."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "add_evidence",
            input_data={
                "thesis_id": request.thesis_id,
                "assumption_id": request.assumption_id,
                "direction": request.direction,
            },
        ):
            async with get_session(venture_id) as session:
                # Create evidence item
                evidence = EvidenceItem(
                    venture_id=venture_id,
                    thesis_id=request.thesis_id,
                    assumption_id=request.assumption_id,
                    source_type=request.source_type,
                    source_id=request.source_id,
                    content=request.content,
                    direction=request.direction,
                    strength=request.strength,
                    recorded_at=datetime.now(UTC),
                )
                session.add(evidence)
                await session.flush()

                evidence_id = evidence.id
                recorded_at = evidence.recorded_at

                # Update thesis evidence count
                thesis_result = await session.execute(
                    select(Thesis).where(
                        Thesis.id == request.thesis_id,
                        Thesis.venture_id == venture_id,
                    )
                )
                thesis = thesis_result.scalar_one()
                thesis.evidence_count += 1

                # Update assumption if specified
                if request.assumption_id:
                    assumption_result = await session.execute(
                        select(ThesisAssumption).where(
                            ThesisAssumption.id == request.assumption_id,
                            ThesisAssumption.thesis_id == request.thesis_id,
                        )
                    )
                    assumption = assumption_result.scalar_one()

                    # Add to assumption's evidence list
                    evidence_entry = {
                        "type": request.source_type,
                        "source": request.source_id,
                        "content": request.content,
                        "direction": request.direction,
                        "strength": request.strength,
                    }
                    updated_evidence = list(assumption.evidence)
                    updated_evidence.append(evidence_entry)
                    assumption.evidence = updated_evidence

                    # Bayesian-inspired confidence update
                    assumption.confidence = _update_confidence(
                        assumption.confidence, request.direction, request.strength
                    )

                    # Auto-update assumption status
                    assumption.status = _derive_assumption_status(
                        assumption.confidence, len(assumption.evidence)
                    )

                # Recalculate thesis confidence as average of assumption confidences
                all_assumptions_result = await session.execute(
                    select(ThesisAssumption).where(
                        ThesisAssumption.thesis_id == request.thesis_id,
                        ThesisAssumption.venture_id == venture_id,
                        ThesisAssumption.deleted_at.is_(None),
                    )
                )
                all_assumptions = list(all_assumptions_result.scalars().all())
                if all_assumptions:
                    thesis.confidence = sum(
                        a.confidence for a in all_assumptions
                    ) / len(all_assumptions)

            await self._event_bus.publish(
                event_type="thesis.evidence.added",
                source_module=MODULE_NAME,
                payload={
                    "thesis_id": request.thesis_id,
                    "assumption_id": request.assumption_id,
                    "evidence_id": evidence_id,
                    "direction": request.direction,
                    "strength": request.strength,
                },
                venture_id=venture_id,
            )

            await self._event_bus.publish(
                event_type="thesis.confidence.updated",
                source_module=MODULE_NAME,
                payload={
                    "thesis_id": request.thesis_id,
                    "thesis_confidence": thesis.confidence,
                    "assumption_id": request.assumption_id,
                    "assumption_confidence": assumption.confidence if request.assumption_id else None,
                },
                venture_id=venture_id,
            )

            logger.info(
                "evidence_added",
                thesis_id=request.thesis_id,
                assumption_id=request.assumption_id,
                evidence_id=evidence_id,
                direction=request.direction,
                strength=request.strength,
            )

            return EvidenceResponse(
                id=evidence_id,
                thesis_id=request.thesis_id,
                assumption_id=request.assumption_id,
                source_type=request.source_type,
                source_id=request.source_id,
                content=request.content,
                direction=request.direction,
                strength=request.strength,
                recorded_at=recorded_at,
            )

    async def get_evidence(
        self, venture_id: str, thesis_id: str, assumption_id: str | None = None
    ) -> list[EvidenceResponse]:
        """Retrieve evidence items for a thesis, optionally filtered by assumption."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            query = select(EvidenceItem).where(
                EvidenceItem.thesis_id == thesis_id,
                EvidenceItem.venture_id == venture_id,
                EvidenceItem.deleted_at.is_(None),
            )
            if assumption_id:
                query = query.where(EvidenceItem.assumption_id == assumption_id)
            query = query.order_by(EvidenceItem.recorded_at.desc())

            result = await session.execute(query)
            items = result.scalars().all()

            return [
                EvidenceResponse(
                    id=item.id,
                    thesis_id=item.thesis_id,
                    assumption_id=item.assumption_id,
                    source_type=item.source_type,
                    source_id=item.source_id,
                    content=item.content,
                    direction=item.direction,
                    strength=item.strength,
                    recorded_at=item.recorded_at,
                )
                for item in items
            ]

    # ------------------------------------------------------------------
    # Kill Signal Monitoring
    # ------------------------------------------------------------------

    async def check_kill_signals(
        self, venture_id: str, thesis_id: str
    ) -> list[str]:
        """Check if any kill signal conditions are met.

        Kill signals trigger when any assumption's confidence drops below 0.2
        (invalidated). Returns list of triggered kill signal descriptions.
        """
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "check_kill_signals"):
            async with get_session(venture_id) as session:
                thesis_result = await session.execute(
                    select(Thesis).where(
                        Thesis.id == thesis_id,
                        Thesis.venture_id == venture_id,
                        Thesis.deleted_at.is_(None),
                    )
                )
                thesis = thesis_result.scalar_one()

                if not thesis.kill_signals:
                    return []

                assumptions_result = await session.execute(
                    select(ThesisAssumption).where(
                        ThesisAssumption.thesis_id == thesis_id,
                        ThesisAssumption.venture_id == venture_id,
                        ThesisAssumption.deleted_at.is_(None),
                    )
                )
                assumptions = list(assumptions_result.scalars().all())

            # Check if any assumptions are invalidated (confidence < 0.2)
            invalidated_assumptions = [
                a for a in assumptions if a.confidence < 0.2
            ]

            triggered_signals: list[str] = []
            if invalidated_assumptions:
                # All kill signals are triggered when assumptions are invalidated
                triggered_signals = list(thesis.kill_signals)

                for signal in triggered_signals:
                    await self._event_bus.publish(
                        event_type="thesis.kill_signal.triggered",
                        source_module=MODULE_NAME,
                        payload={
                            "thesis_id": thesis_id,
                            "signal": signal,
                            "invalidated_assumptions": [
                                {
                                    "id": a.id,
                                    "statement": a.statement,
                                    "confidence": a.confidence,
                                }
                                for a in invalidated_assumptions
                            ],
                        },
                        venture_id=venture_id,
                    )

                logger.warning(
                    "kill_signals_triggered",
                    thesis_id=thesis_id,
                    venture_id=venture_id,
                    signal_count=len(triggered_signals),
                    invalidated_count=len(invalidated_assumptions),
                )

            return triggered_signals

    # ------------------------------------------------------------------
    # LLM-Powered Analysis
    # ------------------------------------------------------------------

    async def generate_validation_plan(
        self, venture_id: str, request: ValidationPlanRequest
    ) -> ValidationPlanResponse:
        """Generate a validation plan using LLM for untested assumptions."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "generate_validation_plan",
            input_data={"thesis_id": request.thesis_id},
        ) as span:
            # Fetch thesis and assumptions
            async with get_session(venture_id) as session:
                thesis_result = await session.execute(
                    select(Thesis).where(
                        Thesis.id == request.thesis_id,
                        Thesis.venture_id == venture_id,
                        Thesis.deleted_at.is_(None),
                    )
                )
                thesis = thesis_result.scalar_one()

                assumptions_result = await session.execute(
                    select(ThesisAssumption).where(
                        ThesisAssumption.thesis_id == request.thesis_id,
                        ThesisAssumption.venture_id == venture_id,
                        ThesisAssumption.deleted_at.is_(None),
                    ).order_by(ThesisAssumption.created_at)
                )
                assumptions = list(assumptions_result.scalars().all())

            # Filter to untested/testing assumptions
            untested = [
                a for a in assumptions if a.status in ("untested", "testing")
            ]

            assumptions_context = []
            for a in untested:
                assumptions_context.append({
                    "statement": a.statement,
                    "risk_level": a.risk_level,
                    "status": a.status,
                    "confidence": a.confidence,
                    "validation_method": a.validation_method,
                    "evidence_count": len(a.evidence),
                })

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a venture validation strategist. Your job is to create "
                        "efficient, prioritized validation plans that test the riskiest "
                        "assumptions first with minimum resources.\n\n"
                        "Principles:\n"
                        "1. Test the riskiest assumptions first (critical > high > medium > low)\n"
                        "2. Prefer cheap, fast experiments over expensive, slow ones\n"
                        "3. Each step should have clear success/failure criteria\n"
                        "4. Consider both qualitative and quantitative methods\n"
                        "5. Estimate realistic effort and time\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Create a validation plan for this venture thesis.\n\n"
                        f"Thesis: {thesis.title}\n"
                        f"Hypothesis: {thesis.hypothesis}\n"
                        f"Current confidence: {thesis.confidence:.2f}\n\n"
                        f"Assumptions needing validation:\n"
                        + json.dumps(assumptions_context, indent=2)
                        + "\n\nRespond with JSON:\n"
                        "{\n"
                        '  "plan": [\n'
                        "    {\n"
                        '      "assumption": "<the assumption being tested>",\n'
                        '      "method": "<validation method: interview, experiment, survey, data analysis, etc.>",\n'
                        '      "success_criteria": "<what would validate this assumption>",\n'
                        '      "effort": "<low|medium|high>",\n'
                        '      "priority": <1-N where 1 is highest priority>\n'
                        "    }\n"
                        "  ],\n"
                        '  "estimated_time": "<total estimated time, e.g. 2-3 weeks>",\n'
                        '  "estimated_cost": "<total estimated cost, e.g. $500-1000>"\n'
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
                metadata={"thesis_id": request.thesis_id},
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            plan_steps = [
                ValidationStep(**step) for step in parsed.get("plan", [])
            ]

            # Store the validation plan on the thesis
            async with get_session(venture_id) as session:
                thesis_result = await session.execute(
                    select(Thesis).where(Thesis.id == request.thesis_id)
                )
                thesis_record = thesis_result.scalar_one()
                thesis_record.validation_plan = parsed

            response = ValidationPlanResponse(
                thesis_id=request.thesis_id,
                plan=plan_steps,
                estimated_time=parsed.get("estimated_time", "unknown"),
                estimated_cost=parsed.get("estimated_cost", "unknown"),
            )

            logger.info(
                "validation_plan_generated",
                thesis_id=request.thesis_id,
                venture_id=venture_id,
                step_count=len(plan_steps),
            )

            return response

    async def generate_memo(
        self, venture_id: str, request: ThesisMemoRequest
    ) -> ThesisMemoResponse:
        """Generate a venture memo summarizing thesis state using LLM."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "generate_memo",
            input_data={"thesis_id": request.thesis_id},
        ) as span:
            # Fetch full thesis context
            async with get_session(venture_id) as session:
                thesis_result = await session.execute(
                    select(Thesis).where(
                        Thesis.id == request.thesis_id,
                        Thesis.venture_id == venture_id,
                        Thesis.deleted_at.is_(None),
                    )
                )
                thesis = thesis_result.scalar_one()

                assumptions_result = await session.execute(
                    select(ThesisAssumption).where(
                        ThesisAssumption.thesis_id == request.thesis_id,
                        ThesisAssumption.venture_id == venture_id,
                        ThesisAssumption.deleted_at.is_(None),
                    ).order_by(ThesisAssumption.created_at)
                )
                assumptions = list(assumptions_result.scalars().all())

                evidence_result = await session.execute(
                    select(EvidenceItem).where(
                        EvidenceItem.thesis_id == request.thesis_id,
                        EvidenceItem.venture_id == venture_id,
                        EvidenceItem.deleted_at.is_(None),
                    ).order_by(EvidenceItem.recorded_at.desc())
                )
                evidence_items = list(evidence_result.scalars().all())

            # Build context for memo generation
            assumptions_context = []
            for a in assumptions:
                assumptions_context.append({
                    "statement": a.statement,
                    "risk_level": a.risk_level,
                    "status": a.status,
                    "confidence": a.confidence,
                    "evidence_count": len(a.evidence),
                })

            evidence_context = []
            for e in evidence_items[:20]:  # Limit to recent 20
                evidence_context.append({
                    "source_type": e.source_type,
                    "content": e.content,
                    "direction": e.direction,
                    "strength": e.strength,
                })

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a venture strategist writing a concise, honest investment memo. "
                        "Your memo should be structured, data-driven, and highlight both "
                        "strengths and risks clearly.\n\n"
                        "Structure:\n"
                        "1. Executive Summary (2-3 sentences)\n"
                        "2. Thesis Statement & Current Status\n"
                        "3. Evidence Summary (what supports, what contradicts)\n"
                        "4. Key Risks & Mitigation\n"
                        "5. Confidence Assessment\n"
                        "6. Recommended Next Actions\n\n"
                        "Be direct. If the evidence is weak or contradictory, say so plainly.\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Write a venture memo for this thesis.\n\n"
                        f"Title: {thesis.title}\n"
                        f"Hypothesis: {thesis.hypothesis}\n"
                        f"Status: {thesis.status}\n"
                        f"Overall Confidence: {thesis.confidence:.2f}\n"
                        f"Total Evidence Count: {thesis.evidence_count}\n"
                        f"Kill Signals: {json.dumps(thesis.kill_signals)}\n\n"
                        f"Assumptions:\n{json.dumps(assumptions_context, indent=2)}\n\n"
                        f"Recent Evidence:\n{json.dumps(evidence_context, indent=2)}\n\n"
                        "Respond with JSON:\n"
                        "{\n"
                        '  "memo": "<full memo text in markdown format>",\n'
                        '  "confidence_summary": {\n'
                        '    "<assumption statement>": <confidence float>,\n'
                        "    ...\n"
                        "  },\n"
                        '  "next_actions": ["<action 1>", "<action 2>", ...]\n'
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.5,
                venture_id=venture_id,
                module_name=MODULE_NAME,
                metadata={"thesis_id": request.thesis_id},
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            response = ThesisMemoResponse(
                thesis_id=request.thesis_id,
                memo=parsed.get("memo", ""),
                confidence_summary=parsed.get("confidence_summary", {}),
                next_actions=parsed.get("next_actions", []),
            )

            logger.info(
                "thesis_memo_generated",
                thesis_id=request.thesis_id,
                venture_id=venture_id,
                memo_length=len(response.memo),
                action_count=len(response.next_actions),
            )

            return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_thesis_response(
        self, thesis: Thesis, assumptions: list[ThesisAssumption]
    ) -> ThesisResponse:
        """Build a ThesisResponse from ORM models."""
        assumption_responses = [
            AssumptionResponse(
                id=a.id,
                thesis_id=a.thesis_id,
                statement=a.statement,
                risk_level=a.risk_level,
                status=a.status,
                confidence=a.confidence,
                evidence_count=len(a.evidence),
                validation_method=a.validation_method,
                created_at=a.created_at,
            )
            for a in assumptions
        ]

        return ThesisResponse(
            id=thesis.id,
            venture_id=thesis.venture_id,
            title=thesis.title,
            hypothesis=thesis.hypothesis,
            status=thesis.status,
            confidence=thesis.confidence,
            evidence_count=thesis.evidence_count,
            assumptions=assumption_responses,
            kill_signals=thesis.kill_signals,
            validation_plan=thesis.validation_plan,
            created_at=thesis.created_at,
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _update_confidence(current: float, direction: str, strength: float) -> float:
    """Bayesian-inspired confidence update.

    When evidence supports, confidence moves toward 1.0.
    When evidence contradicts, confidence moves toward 0.0.
    Neutral evidence does not change confidence.
    """
    if direction == "supports":
        # Move toward 1.0, scaled by strength
        return current + (1.0 - current) * strength * 0.3
    elif direction == "contradicts":
        # Move toward 0.0, scaled by strength
        return current - current * strength * 0.3
    return current  # neutral — no change


def _derive_assumption_status(confidence: float, evidence_count: int) -> str:
    """Derive assumption status from confidence level and evidence."""
    if confidence > 0.8:
        return "validated"
    elif confidence < 0.2:
        return "invalidated"
    elif evidence_count > 0:
        return "testing"
    return "untested"


def _parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
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
        return {}
