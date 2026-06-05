"""Human Review Engine endpoints."""

from fastapi import APIRouter, HTTPException

from ai_flywheel.modules.agent_runtime.human_review.schemas import (
    ReviewDecision,
    ReviewQueue,
    ReviewRequest,
    ReviewResponse,
)
from ai_flywheel.modules.agent_runtime.human_review.service import HumanReviewEngine

router = APIRouter()
service = HumanReviewEngine()


@router.post("/", response_model=ReviewResponse)
async def submit_for_review(venture_id: str, request: ReviewRequest):
    return await service.submit_for_review(venture_id, request)


@router.post("/decide", response_model=ReviewResponse)
async def decide(venture_id: str, data: ReviewDecision):
    try:
        return await service.decide(venture_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/queue", response_model=ReviewQueue)
async def get_queue(venture_id: str, status: str | None = "pending", priority: str | None = None):
    return await service.get_queue(venture_id, status, priority)
