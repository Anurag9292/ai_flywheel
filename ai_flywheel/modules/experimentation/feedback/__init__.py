"""Feedback Collector — Module #33 (Phase 3, Experimentation group).

Collects explicit, implicit, and automated feedback from all modules.
Routes feedback to target modules via the event bus for continuous improvement.

Usage:
    from ai_flywheel.modules.experimentation.feedback import (
        FeedbackCollector,
        FeedbackItem,
    )

    collector = FeedbackCollector()
    feedback = await collector.collect(venture_id, data)
    summary = await collector.get_summary(venture_id, entity_id, entity_type)
"""

from .models import FeedbackItem
from .schemas import (
    FeedbackCreate,
    FeedbackQuery,
    FeedbackResponse,
    FeedbackSummary,
)
from .service import FeedbackCollector

__all__ = [
    "FeedbackCollector",
    "FeedbackCreate",
    "FeedbackItem",
    "FeedbackQuery",
    "FeedbackResponse",
    "FeedbackSummary",
]
