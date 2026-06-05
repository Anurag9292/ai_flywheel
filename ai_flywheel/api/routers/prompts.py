"""Prompt Studio endpoints."""

from fastapi import APIRouter, HTTPException

from ai_flywheel.modules.agent_runtime.prompt_studio.schemas import (
    PromptRenderRequest,
    PromptRenderResponse,
    PromptTemplateCreate,
    PromptTemplateResponse,
)
from ai_flywheel.modules.agent_runtime.prompt_studio.service import PromptStudio

router = APIRouter()
service = PromptStudio()


@router.post("/", response_model=PromptTemplateResponse)
async def create_template(venture_id: str, data: PromptTemplateCreate):
    return await service.create_template(venture_id, data)


@router.get("/", response_model=list[PromptTemplateResponse])
async def list_templates(venture_id: str):
    return await service.list_templates(venture_id)


@router.post("/render", response_model=PromptRenderResponse)
async def render(venture_id: str, request: PromptRenderRequest):
    try:
        return await service.render(venture_id, request)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
