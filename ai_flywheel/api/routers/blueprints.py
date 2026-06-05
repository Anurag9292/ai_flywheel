"""Workflow Blueprint Engine endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.product_intelligence.workflow_blueprint.schemas import (
    BlueprintCreate,
    BlueprintResponse,
    CompileRequest,
    CompileResult,
    GenerateBlueprintRequest,
    GenerateBlueprintResult,
    ValidateBlueprintRequest,
    ValidateBlueprintResult,
)
from ai_flywheel.modules.product_intelligence.workflow_blueprint.service import (
    WorkflowBlueprintEngine,
)

router = APIRouter()
service = WorkflowBlueprintEngine()


@router.post("/", response_model=BlueprintResponse)
async def create_blueprint(venture_id: str, data: BlueprintCreate):
    return await service.create_blueprint(venture_id, data)


@router.get("/", response_model=list[BlueprintResponse])
async def list_blueprints(venture_id: str):
    return await service.list_blueprints(venture_id)


@router.post("/generate", response_model=GenerateBlueprintResult)
async def generate_from_description(venture_id: str, request: GenerateBlueprintRequest):
    return await service.generate_from_description(venture_id, request)


@router.post("/validate", response_model=ValidateBlueprintResult)
async def validate(venture_id: str, request: ValidateBlueprintRequest):
    return await service.validate(venture_id, request)


@router.post("/compile", response_model=CompileResult)
async def compile(venture_id: str, request: CompileRequest):
    return await service.compile(venture_id, request)
