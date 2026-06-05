"""Data Quality Engine endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.data_knowledge.quality.schemas import (
    QualityCheckRequest,
    QualityCheckResult,
    QualityRuleCreate,
    QualityRuleResponse,
)
from ai_flywheel.modules.data_knowledge.quality.service import DataQualityEngine

router = APIRouter()
service = DataQualityEngine()


@router.post("/rules", response_model=QualityRuleResponse)
async def create_rule(venture_id: str, data: QualityRuleCreate):
    return await service.create_rule(venture_id, data)


@router.get("/rules", response_model=list[QualityRuleResponse])
async def list_rules(venture_id: str):
    return await service.list_rules(venture_id)


@router.post("/check", response_model=QualityCheckResult)
async def check(venture_id: str, request: QualityCheckRequest):
    return await service.check(venture_id, request)
