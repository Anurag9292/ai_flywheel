"""Feedback Collector endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.experimentation.feedback.schemas import (
    FeedbackCreate,
    FeedbackQuery,
    FeedbackResponse,
    FeedbackSummary,
)
from ai_flywheel.modules.experimentation.feedback.service import FeedbackCollector

router = APIRouter()
service = FeedbackCollector()


@router.post("/", response_model=FeedbackResponse)
async def collect(venture_id: str, data: FeedbackCreate):
    return await service.collect(venture_id, data)


@router.get("/", response_model=list[FeedbackResponse])
async def get_feedback(
    venture_id: str,
    entity_id: str | None = None,
    entity_type: str | None = None,
    feedback_type: str | None = None,
    category: str | None = None,
    source_module: str | None = None,
    limit: int = 50,
):
    query = FeedbackQuery(
        entity_id=entity_id,
        entity_type=entity_type,
        feedback_type=feedback_type,
        category=category,
        source_module=source_module,
        limit=limit,
    )
    return await service.get_feedback(venture_id, query)


@router.get("/summary", response_model=FeedbackSummary)
async def get_summary(venture_id: str, entity_id: str, entity_type: str):
    return await service.get_summary(venture_id, entity_id, entity_type)
