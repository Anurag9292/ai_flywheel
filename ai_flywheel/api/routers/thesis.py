"""Venture Thesis Engine endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.product_intelligence.venture_thesis.schemas import (
    AddEvidenceRequest,
    EvidenceResponse,
    ThesisCreate,
    ThesisMemoRequest,
    ThesisMemoResponse,
    ThesisResponse,
    ValidationPlanRequest,
    ValidationPlanResponse,
)
from ai_flywheel.modules.product_intelligence.venture_thesis.service import (
    VentureThesisEngine,
)

router = APIRouter()
service = VentureThesisEngine()


@router.post("/", response_model=ThesisResponse)
async def create_thesis(venture_id: str, data: ThesisCreate):
    return await service.create_thesis(venture_id, data)


@router.get("/", response_model=list[ThesisResponse])
async def list_theses(venture_id: str):
    return await service.list_theses(venture_id)


@router.post("/evidence", response_model=EvidenceResponse)
async def add_evidence(venture_id: str, request: AddEvidenceRequest):
    return await service.add_evidence(venture_id, request)


@router.post("/validation-plan", response_model=ValidationPlanResponse)
async def generate_validation_plan(venture_id: str, request: ValidationPlanRequest):
    return await service.generate_validation_plan(venture_id, request)


@router.post("/memo", response_model=ThesisMemoResponse)
async def generate_memo(venture_id: str, request: ThesisMemoRequest):
    return await service.generate_memo(venture_id, request)
