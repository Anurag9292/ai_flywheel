# ruff: noqa: E501
"""Market & Signal Intelligence — Service layer.

Orchestrates LLM-powered market signal analysis, report generation,
and opportunity scoring.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.llm import generate
from ai_flywheel.core.traces import get_tracer

from .models import MarketReport, MarketSignal, SignalSource
from .schemas import (
    AnalyzeSignalsRequest,
    AnalyzeSignalsResult,
    MarketReportRequest,
    MarketReportResponse,
    MarketSignalResponse,
    OpportunityScore,
    SignalSourceCreate,
    SignalSourceResponse,
)

logger = structlog.get_logger()

MODULE_NAME = "market_intelligence"


def _parse_json_response(text: str) -> dict | list:
    """Safely parse JSON from LLM response, handling code fences."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return json.loads(cleaned)


class MarketIntelligence:
    """Market & Signal Intelligence service."""

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    # ------------------------------------------------------------------
    # Signal Sources
    # ------------------------------------------------------------------

    async def create_source(
        self, venture_id: str, data: SignalSourceCreate
    ) -> SignalSourceResponse:
        """Register a new signal source for scanning."""
        async with self._tracer.span(MODULE_NAME, "create_source"):
            async with get_session(venture_id) as session:
                source = SignalSource(
                    venture_id=venture_id,
                    name=data.name,
                    source_type=data.source_type,
                    url=data.url,
                    config=data.config,
                    is_active=True,
                )
                session.add(source)
                await session.flush()

                response = SignalSourceResponse.model_validate(source)

            await self._event_bus.publish(
                event_type="market.source.created",
                source_module=MODULE_NAME,
                payload={"source_id": response.id, "source_type": data.source_type},
                venture_id=venture_id,
            )

            logger.info(
                "signal_source_created",
                venture_id=venture_id,
                source_id=response.id,
                source_type=data.source_type,
            )
            return response

    async def list_sources(self, venture_id: str) -> list[SignalSourceResponse]:
        """List all active signal sources for a venture."""
        async with self._tracer.span(MODULE_NAME, "list_sources"):
            async with get_session(venture_id) as session:
                stmt = (
                    select(SignalSource)
                    .where(SignalSource.venture_id == venture_id)
                    .where(SignalSource.is_active.is_(True))
                    .where(SignalSource.deleted_at.is_(None))
                    .order_by(SignalSource.created_at.desc())
                )
                result = await session.execute(stmt)
                sources = result.scalars().all()
                return [SignalSourceResponse.model_validate(s) for s in sources]

    # ------------------------------------------------------------------
    # Signal Analysis
    # ------------------------------------------------------------------

    async def analyze_signals(
        self, venture_id: str, request: AnalyzeSignalsRequest
    ) -> AnalyzeSignalsResult:
        """Analyze raw text to extract and score market signals via LLM."""
        async with self._tracer.span(
            MODULE_NAME,
            "analyze_signals",
            input_data={"domain": request.domain, "text_length": len(request.signals_text)},
        ) as span:
            focus_section = ""
            if request.focus_areas:
                focus_section = (
                    f"\nFocus particularly on these areas: {', '.join(request.focus_areas)}"
                )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a market intelligence analyst. Extract market signals "
                        "from the provided text. For each signal, classify its type and "
                        "score its relevance and impact.\n\n"
                        "Signal types: competitor_move, trend, funding, launch, "
                        "regulatory, opportunity, threat\n\n"
                        "Respond with valid JSON only, no markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Domain: {request.domain}\n"
                        f"{focus_section}\n\n"
                        f"Analyze the following text and extract all market signals:\n\n"
                        f"{request.signals_text}\n\n"
                        "Respond in this exact JSON format:\n"
                        "{\n"
                        '  "signals": [\n'
                        "    {\n"
                        '      "signal_type": "competitor_move|trend|funding|launch|regulatory|opportunity|threat",\n'
                        '      "title": "Brief title",\n'
                        '      "summary": "2-3 sentence explanation",\n'
                        '      "relevance_score": 0.0-1.0,\n'
                        '      "impact_score": 0.0-1.0,\n'
                        '      "tags": ["tag1", "tag2"]\n'
                        "    }\n"
                        "  ],\n"
                        '  "patterns": ["pattern1", "pattern2"],\n'
                        '  "summary": "Overall summary of signals detected"\n'
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
            )

            span.set_cost(
                llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            # Persist signals to database
            signal_responses: list[MarketSignalResponse] = []
            now = datetime.now(UTC)

            async with get_session(venture_id) as session:
                for sig_data in parsed.get("signals", []):
                    signal = MarketSignal(
                        venture_id=venture_id,
                        source_id=None,
                        signal_type=sig_data.get("signal_type", "trend"),
                        title=sig_data.get("title", ""),
                        summary=sig_data.get("summary", ""),
                        relevance_score=float(sig_data.get("relevance_score", 0.5)),
                        impact_score=float(sig_data.get("impact_score", 0.5)),
                        raw_data=sig_data,
                        tags=sig_data.get("tags", []),
                        detected_at=now,
                    )
                    session.add(signal)
                    await session.flush()

                    signal_responses.append(
                        MarketSignalResponse(
                            id=signal.id,
                            signal_type=signal.signal_type,
                            title=signal.title,
                            summary=signal.summary,
                            relevance_score=signal.relevance_score,
                            impact_score=signal.impact_score,
                            tags=signal.tags,
                            detected_at=signal.detected_at,
                        )
                    )

            result = AnalyzeSignalsResult(
                signals=signal_responses,
                patterns=parsed.get("patterns", []),
                summary=parsed.get("summary", ""),
            )

            await self._event_bus.publish(
                event_type="market.signals.analyzed",
                source_module=MODULE_NAME,
                payload={
                    "domain": request.domain,
                    "signals_count": len(signal_responses),
                    "patterns": result.patterns,
                },
                venture_id=venture_id,
            )

            logger.info(
                "signals_analyzed",
                venture_id=venture_id,
                domain=request.domain,
                signals_count=len(signal_responses),
            )
            return result

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------

    async def generate_report(
        self, venture_id: str, request: MarketReportRequest
    ) -> MarketReportResponse:
        """Synthesize stored signals into an actionable market report."""
        async with self._tracer.span(
            MODULE_NAME,
            "generate_report",
            input_data={"report_type": request.report_type, "period": request.period},
        ) as span:
            # Fetch recent signals for context
            async with get_session(venture_id) as session:
                stmt = (
                    select(MarketSignal)
                    .where(MarketSignal.venture_id == venture_id)
                    .where(MarketSignal.deleted_at.is_(None))
                    .order_by(MarketSignal.detected_at.desc())
                    .limit(100)
                )
                result = await session.execute(stmt)
                signals = result.scalars().all()

            signals_context = "\n".join(
                f"- [{s.signal_type}] {s.title}: {s.summary} "
                f"(relevance: {s.relevance_score:.2f}, impact: {s.impact_score:.2f})"
                for s in signals
            )

            focus_section = ""
            if request.focus_areas:
                focus_section = (
                    f"\nFocus areas: {', '.join(request.focus_areas)}"
                )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a senior market analyst producing actionable intelligence "
                        "reports for business leaders. Write clear, concise reports with "
                        "specific recommendations.\n\n"
                        "Respond with valid JSON only, no markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Generate a {request.report_type} market intelligence report "
                        f"for the {request.period} period.\n"
                        f"Domain: {request.domain}\n"
                        f"{focus_section}\n\n"
                        f"Signals detected ({len(signals)} total):\n"
                        f"{signals_context}\n\n"
                        "Respond in this exact JSON format:\n"
                        "{\n"
                        '  "content": "Full report text in markdown format",\n'
                        '  "key_findings": ["finding1", "finding2", ...],\n'
                        '  "recommendations": ["recommendation1", "recommendation2", ...]\n'
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
            )

            span.set_cost(
                llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            # Persist the report
            async with get_session(venture_id) as session:
                report = MarketReport(
                    venture_id=venture_id,
                    report_type=request.report_type,
                    period=request.period,
                    content=parsed.get("content", ""),
                    signals_analyzed=len(signals),
                    key_findings=parsed.get("key_findings", []),
                    recommendations=parsed.get("recommendations", []),
                )
                session.add(report)
                await session.flush()

                response = MarketReportResponse(
                    id=report.id,
                    report_type=report.report_type,
                    period=report.period,
                    content=report.content,
                    signals_analyzed=report.signals_analyzed,
                    key_findings=report.key_findings,
                    recommendations=report.recommendations,
                    created_at=report.created_at,
                )

            await self._event_bus.publish(
                event_type="market.report.generated",
                source_module=MODULE_NAME,
                payload={
                    "report_id": response.id,
                    "report_type": request.report_type,
                    "signals_analyzed": len(signals),
                },
                venture_id=venture_id,
            )

            logger.info(
                "report_generated",
                venture_id=venture_id,
                report_id=response.id,
                report_type=request.report_type,
                signals_analyzed=len(signals),
            )
            return response

    # ------------------------------------------------------------------
    # Opportunity Scoring
    # ------------------------------------------------------------------

    async def score_opportunity(
        self, venture_id: str, opportunity_description: str, domain: str
    ) -> OpportunityScore:
        """Multi-factor opportunity scoring via LLM."""
        async with self._tracer.span(
            MODULE_NAME,
            "score_opportunity",
            input_data={"domain": domain},
        ) as span:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a venture analyst evaluating market opportunities. "
                        "Score each opportunity on multiple factors with clear reasoning.\n\n"
                        "Respond with valid JSON only, no markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Domain: {domain}\n\n"
                        f"Evaluate this opportunity:\n{opportunity_description}\n\n"
                        "Respond in this exact JSON format:\n"
                        "{\n"
                        '  "opportunity": "One-line summary of the opportunity",\n'
                        '  "market_size_signal": "small|medium|large|massive — with brief reasoning",\n'
                        '  "competition_level": "low|moderate|high|saturated — with brief reasoning",\n'
                        '  "timing": "too_early|early|good|late|too_late — with brief reasoning",\n'
                        '  "overall_score": 0.0-1.0\n'
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
            )

            span.set_cost(
                llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            result = OpportunityScore(
                opportunity=parsed.get("opportunity", opportunity_description[:100]),
                market_size_signal=parsed.get("market_size_signal", "medium"),
                competition_level=parsed.get("competition_level", "moderate"),
                timing=parsed.get("timing", "good"),
                overall_score=float(parsed.get("overall_score", 0.5)),
            )

            await self._event_bus.publish(
                event_type="market.opportunity.scored",
                source_module=MODULE_NAME,
                payload={
                    "opportunity": result.opportunity,
                    "overall_score": result.overall_score,
                    "domain": domain,
                },
                venture_id=venture_id,
            )

            logger.info(
                "opportunity_scored",
                venture_id=venture_id,
                overall_score=result.overall_score,
                domain=domain,
            )
            return result

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    async def get_signals(
        self,
        venture_id: str,
        signal_type: str | None = None,
        min_relevance: float = 0.0,
        limit: int = 50,
    ) -> list[MarketSignalResponse]:
        """Retrieve stored signals with optional filtering."""
        async with self._tracer.span(MODULE_NAME, "get_signals"):
            async with get_session(venture_id) as session:
                stmt = (
                    select(MarketSignal)
                    .where(MarketSignal.venture_id == venture_id)
                    .where(MarketSignal.deleted_at.is_(None))
                    .where(MarketSignal.relevance_score >= min_relevance)
                )

                if signal_type is not None:
                    stmt = stmt.where(MarketSignal.signal_type == signal_type)

                stmt = stmt.order_by(MarketSignal.detected_at.desc()).limit(limit)

                result = await session.execute(stmt)
                signals = result.scalars().all()
                return [MarketSignalResponse.model_validate(s) for s in signals]

    async def get_reports(
        self,
        venture_id: str,
        report_type: str | None = None,
    ) -> list[MarketReportResponse]:
        """Retrieve generated reports with optional type filtering."""
        async with self._tracer.span(MODULE_NAME, "get_reports"):
            async with get_session(venture_id) as session:
                stmt = (
                    select(MarketReport)
                    .where(MarketReport.venture_id == venture_id)
                    .where(MarketReport.deleted_at.is_(None))
                )

                if report_type is not None:
                    stmt = stmt.where(MarketReport.report_type == report_type)

                stmt = stmt.order_by(MarketReport.created_at.desc())

                result = await session.execute(stmt)
                reports = result.scalars().all()
                return [MarketReportResponse.model_validate(r) for r in reports]
