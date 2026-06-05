"""Pattern Library service — CRUD, search, confidence tracking, and recommendations."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select

from ai_flywheel.core.database import get_global_session
from ai_flywheel.core.events import get_event_bus

from .models import Pattern, PatternApplication
from .schemas import (
    ApplyPatternRequest,
    ApplyPatternResult,
    PatternCreate,
    PatternResponse,
    PatternSearchRequest,
    PatternSearchResult,
)

logger = structlog.get_logger()


def _to_response(pattern: Pattern) -> PatternResponse:
    """Convert a Pattern ORM object to a PatternResponse."""
    return PatternResponse(
        id=pattern.id,
        name=pattern.name,
        description=pattern.description,
        pattern_type=pattern.pattern_type,
        content=pattern.content,
        tags=pattern.tags,
        source_venture_id=pattern.source_venture_id,
        success_count=pattern.success_count,
        failure_count=pattern.failure_count,
        confidence_score=pattern.confidence_score,
        version=pattern.version,
        is_active=pattern.is_active,
        created_at=pattern.created_at,
    )


class PatternLibrary:
    """Service for managing cross-venture patterns."""

    async def create_pattern(self, data: PatternCreate) -> PatternResponse:
        """Create a new pattern (global, not venture-scoped)."""
        async with get_global_session() as session:
            pattern = Pattern(
                name=data.name,
                description=data.description,
                pattern_type=data.pattern_type,
                content=data.content,
                tags=data.tags,
                source_venture_id=data.source_venture_id,
            )
            session.add(pattern)
            await session.flush()

            response = _to_response(pattern)

        event_bus = get_event_bus()
        await event_bus.publish(
            event_type="pattern.created",
            source_module="pattern_library",
            payload={"pattern_id": response.id, "name": response.name},
        )

        logger.info("pattern_created", pattern_id=response.id, name=response.name)
        return response

    async def get_pattern(self, pattern_id: str) -> PatternResponse:
        """Get a pattern by ID."""
        async with get_global_session() as session:
            result = await session.execute(
                select(Pattern).where(Pattern.id == pattern_id, Pattern.is_active.is_(True))
            )
            pattern = result.scalar_one()
            return _to_response(pattern)

    async def search(self, request: PatternSearchRequest) -> PatternSearchResult:
        """Search patterns by keyword, type, tags, and confidence."""
        async with get_global_session() as session:
            query = select(Pattern).where(Pattern.is_active.is_(True))

            if request.pattern_type:
                query = query.where(Pattern.pattern_type == request.pattern_type)

            if request.min_confidence > 0.0:
                query = query.where(Pattern.confidence_score >= request.min_confidence)

            if request.query:
                like_expr = f"%{request.query}%"
                query = query.where(
                    Pattern.name.ilike(like_expr) | Pattern.description.ilike(like_expr)
                )

            # Count total before limit
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar_one()

            # Apply limit and ordering
            query = query.order_by(Pattern.confidence_score.desc()).limit(request.limit)
            result = await session.execute(query)
            patterns = result.scalars().all()

            return PatternSearchResult(
                patterns=[_to_response(p) for p in patterns],
                total=total,
            )

    async def apply_pattern(self, request: ApplyPatternRequest) -> ApplyPatternResult:
        """Record a pattern application and update confidence score."""
        async with get_global_session() as session:
            # Get the pattern
            result = await session.execute(
                select(Pattern).where(Pattern.id == request.pattern_id)
            )
            pattern = result.scalar_one()

            # Record the application
            application = PatternApplication(
                venture_id=request.venture_id,
                pattern_id=request.pattern_id,
                outcome=request.outcome,
                notes=request.notes or None,
                applied_at=datetime.now(UTC),
            )
            session.add(application)

            # Update counters
            if request.outcome == "success":
                pattern.success_count += 1
            elif request.outcome == "failure":
                pattern.failure_count += 1
            else:
                # partial counts as half success
                pattern.success_count += 1

            # Recalculate confidence
            pattern.confidence_score = pattern.success_count / max(
                pattern.success_count + pattern.failure_count, 1
            )

            await session.flush()

            # Count total applications
            count_result = await session.execute(
                select(func.count())
                .select_from(PatternApplication)
                .where(PatternApplication.pattern_id == request.pattern_id)
            )
            total_applications = count_result.scalar_one()

            new_confidence = pattern.confidence_score

        event_bus = get_event_bus()
        await event_bus.publish(
            event_type="pattern.applied",
            source_module="pattern_library",
            payload={
                "pattern_id": request.pattern_id,
                "venture_id": request.venture_id,
                "outcome": request.outcome,
                "new_confidence": new_confidence,
            },
        )

        return ApplyPatternResult(
            pattern_id=request.pattern_id,
            new_confidence=new_confidence,
            total_applications=total_applications,
        )

    async def recommend_for_venture(
        self, venture_id: str, context: str = ""
    ) -> list[PatternResponse]:
        """Recommend top patterns for a venture by confidence score."""
        async with get_global_session() as session:
            query = (
                select(Pattern)
                .where(Pattern.is_active.is_(True), Pattern.confidence_score > 0.0)
                .order_by(Pattern.confidence_score.desc())
                .limit(10)
            )
            result = await session.execute(query)
            patterns = result.scalars().all()

        event_bus = get_event_bus()
        await event_bus.publish(
            event_type="pattern.recommended",
            source_module="pattern_library",
            payload={
                "venture_id": venture_id,
                "count": len(patterns),
                "context": context,
            },
        )

        return [_to_response(p) for p in patterns]

    async def list_patterns(self, pattern_type: str | None = None) -> list[PatternResponse]:
        """List all active patterns, optionally filtered by type."""
        async with get_global_session() as session:
            query = select(Pattern).where(Pattern.is_active.is_(True))

            if pattern_type:
                query = query.where(Pattern.pattern_type == pattern_type)

            query = query.order_by(Pattern.created_at.desc())
            result = await session.execute(query)
            patterns = result.scalars().all()

            return [_to_response(p) for p in patterns]
