"""Feedback Collector service.

The FeedbackCollector ingests feedback signals from across the platform,
scores their quality, stores them, and routes them to target modules
via the event bus for continuous improvement loops.
"""

from __future__ import annotations

import structlog
from sqlalchemy import func, select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .models import FeedbackItem
from .schemas import (
    FeedbackCreate,
    FeedbackQuery,
    FeedbackResponse,
    FeedbackSummary,
)

logger = structlog.get_logger()


class FeedbackCollector:
    """Collects, scores, and routes feedback for continuous improvement.

    Usage:
        collector = FeedbackCollector()
        feedback = await collector.collect(venture_id, data)
        summary = await collector.get_summary(venture_id, entity_id, "agent_output")
    """

    def __init__(self) -> None:
        self._event_bus = get_event_bus()
        self._tracer = get_tracer()

    async def collect(
        self, venture_id: str, data: FeedbackCreate
    ) -> FeedbackResponse:
        """Collect a feedback item, score it, store it, and route to target module."""
        quality_score = self.score_quality(data)

        async with get_session(venture_id) as session:
            item = FeedbackItem(
                venture_id=venture_id,
                feedback_type=data.feedback_type,
                category=data.category,
                source_module=data.source_module,
                target_module=data.target_module,
                entity_id=data.entity_id,
                entity_type=data.entity_type,
                rating=data.rating,
                correction_text=data.correction_text,
                context=data.context,
                user_id=data.user_id,
                session_id=data.session_id,
                quality_score=quality_score,
            )
            session.add(item)
            await session.flush()

            response = FeedbackResponse.model_validate(item)

        # Emit general feedback collected event
        await self._event_bus.publish(
            event_type="feedback.collected",
            source_module="feedback_collector",
            payload={
                "feedback_id": response.id,
                "feedback_type": data.feedback_type,
                "category": data.category,
                "entity_id": data.entity_id,
                "entity_type": data.entity_type,
                "source_module": data.source_module,
                "quality_score": quality_score,
            },
            venture_id=venture_id,
        )

        # Route to target module via specific event
        target = data.target_module or data.source_module
        await self._event_bus.publish(
            event_type=f"feedback.received.{target}",
            source_module="feedback_collector",
            payload={
                "feedback_id": response.id,
                "feedback_type": data.feedback_type,
                "category": data.category,
                "entity_id": data.entity_id,
                "entity_type": data.entity_type,
                "rating": data.rating,
                "correction_text": data.correction_text,
                "context": data.context,
                "quality_score": quality_score,
            },
            venture_id=venture_id,
        )

        logger.info(
            "feedback_collected",
            venture_id=venture_id,
            feedback_id=response.id,
            feedback_type=data.feedback_type,
            category=data.category,
            entity_id=data.entity_id,
            target_module=target,
            quality_score=quality_score,
        )

        return response

    async def get_feedback(
        self, venture_id: str, query: FeedbackQuery
    ) -> list[FeedbackResponse]:
        """Query feedback items with optional filters."""
        async with get_session(venture_id) as session:
            stmt = select(FeedbackItem).where(
                FeedbackItem.venture_id == venture_id,
                FeedbackItem.deleted_at.is_(None),
            )

            if query.entity_id:
                stmt = stmt.where(FeedbackItem.entity_id == query.entity_id)
            if query.entity_type:
                stmt = stmt.where(FeedbackItem.entity_type == query.entity_type)
            if query.feedback_type:
                stmt = stmt.where(FeedbackItem.feedback_type == query.feedback_type)
            if query.category:
                stmt = stmt.where(FeedbackItem.category == query.category)
            if query.source_module:
                stmt = stmt.where(FeedbackItem.source_module == query.source_module)

            stmt = stmt.order_by(FeedbackItem.created_at.desc()).limit(query.limit)

            result = await session.execute(stmt)
            items = result.scalars().all()

            return [FeedbackResponse.model_validate(item) for item in items]

    async def get_summary(
        self, venture_id: str, entity_id: str, entity_type: str
    ) -> FeedbackSummary:
        """Get an aggregated summary of feedback for a specific entity."""
        async with get_session(venture_id) as session:
            base_filter = [
                FeedbackItem.venture_id == venture_id,
                FeedbackItem.entity_id == entity_id,
                FeedbackItem.entity_type == entity_type,
                FeedbackItem.deleted_at.is_(None),
            ]

            # Total count
            total_stmt = select(func.count()).where(*base_filter)
            total_result = await session.execute(total_stmt)
            total_feedback = total_result.scalar_one()

            # Average rating (only for items with ratings)
            avg_stmt = select(func.avg(FeedbackItem.rating)).where(
                *base_filter,
                FeedbackItem.rating.isnot(None),
            )
            avg_result = await session.execute(avg_stmt)
            avg_rating_raw = avg_result.scalar_one()
            avg_rating = float(avg_rating_raw) if avg_rating_raw is not None else None

            # Positive count (rating >= 3 for 1-5 scale, or == 1 for thumbs)
            positive_stmt = select(func.count()).where(
                *base_filter,
                FeedbackItem.rating.isnot(None),
                FeedbackItem.rating >= 3.0,
            )
            positive_result = await session.execute(positive_stmt)
            positive_count = positive_result.scalar_one()

            # Negative count (rating < 3)
            negative_stmt = select(func.count()).where(
                *base_filter,
                FeedbackItem.rating.isnot(None),
                FeedbackItem.rating < 3.0,
            )
            negative_result = await session.execute(negative_stmt)
            negative_count = negative_result.scalar_one()

            # Correction count
            correction_stmt = select(func.count()).where(
                *base_filter,
                FeedbackItem.category == "correction",
            )
            correction_result = await session.execute(correction_stmt)
            correction_count = correction_result.scalar_one()

            # Recent feedback (last 10)
            recent_stmt = (
                select(FeedbackItem)
                .where(*base_filter)
                .order_by(FeedbackItem.created_at.desc())
                .limit(10)
            )
            recent_result = await session.execute(recent_stmt)
            recent_items = recent_result.scalars().all()
            recent_feedback = [
                FeedbackResponse.model_validate(item) for item in recent_items
            ]

        return FeedbackSummary(
            entity_id=entity_id,
            entity_type=entity_type,
            total_feedback=total_feedback,
            avg_rating=avg_rating,
            positive_count=positive_count,
            negative_count=negative_count,
            correction_count=correction_count,
            recent_feedback=recent_feedback,
        )

    async def get_module_feedback(
        self, venture_id: str, module_name: str, limit: int = 50
    ) -> list[FeedbackResponse]:
        """Get all feedback targeting a specific module."""
        async with get_session(venture_id) as session:
            stmt = (
                select(FeedbackItem)
                .where(
                    FeedbackItem.venture_id == venture_id,
                    FeedbackItem.deleted_at.is_(None),
                    (FeedbackItem.target_module == module_name)
                    | (FeedbackItem.source_module == module_name),
                )
                .order_by(FeedbackItem.created_at.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            items = result.scalars().all()

            return [FeedbackResponse.model_validate(item) for item in items]

    def score_quality(self, feedback: FeedbackCreate) -> float:
        """Heuristic quality scoring for feedback signals.

        Scoring rules:
        - Explicit feedback > Implicit > Automated (base score)
        - With context > Without context (bonus)
        - With correction text > Without (bonus for correction category)
        - With user_id > Anonymous (bonus)
        """
        # Base score by feedback type
        type_scores: dict[str, float] = {
            "explicit": 1.0,
            "implicit": 0.6,
            "automated": 0.4,
        }
        score = type_scores.get(feedback.feedback_type, 0.5)

        # Context richness bonus
        if feedback.context:
            context_keys = len(feedback.context)
            score += min(0.2, context_keys * 0.05)  # Up to +0.2

        # Correction text bonus (valuable signal)
        if feedback.correction_text:
            score += 0.15

        # Identified user bonus
        if feedback.user_id:
            score += 0.1

        # Session context bonus
        if feedback.session_id:
            score += 0.05

        # Cap at 1.0
        return min(1.0, round(score, 3))
