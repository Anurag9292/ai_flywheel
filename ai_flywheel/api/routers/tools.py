"""Tool Forge endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.agent_runtime.tool_forge.schemas import (
    ToolCreate,
    ToolInvokeRequest,
    ToolInvokeResult,
    ToolResponse,
    ToolSearchRequest,
    ToolSearchResult,
)
from ai_flywheel.modules.agent_runtime.tool_forge.service import ToolForge

router = APIRouter()
service = ToolForge()


@router.post("/", response_model=ToolResponse)
async def register_tool(venture_id: str, data: ToolCreate):
    return await service.register_tool(venture_id, data)


@router.get("/", response_model=list[ToolResponse])
async def list_tools(venture_id: str, category: str | None = None):
    return await service.list_tools(venture_id, category)


@router.post("/invoke", response_model=ToolInvokeResult)
async def invoke(venture_id: str, request: ToolInvokeRequest):
    return await service.invoke(venture_id, request)


@router.post("/search", response_model=ToolSearchResult)
async def search(venture_id: str, request: ToolSearchRequest):
    return await service.search(venture_id, request)
