"""Memory Engine endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.agent_runtime.memory_engine.schemas import (
    MemoryContext,
    MemoryQuery,
    MemoryResponse,
    MemoryStore,
)
from ai_flywheel.modules.agent_runtime.memory_engine.service import MemoryEngine

router = APIRouter()
service = MemoryEngine()


@router.post("/", response_model=MemoryResponse)
async def store(venture_id: str, data: MemoryStore):
    return await service.store(venture_id, data)


@router.post("/recall", response_model=list[MemoryResponse])
async def recall(venture_id: str, query: MemoryQuery):
    return await service.recall(venture_id, query)


@router.post("/context", response_model=MemoryContext)
async def get_context(venture_id: str, agent_id: str, token_budget: int = 4000):
    return await service.get_context(venture_id, agent_id, token_budget)
