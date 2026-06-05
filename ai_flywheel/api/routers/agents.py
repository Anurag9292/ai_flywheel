"""Agent management and execution endpoints."""
from fastapi import APIRouter, HTTPException

from ai_flywheel.modules.agent_runtime.agent_factory.schemas import (
    AgentBlueprintCreate,
    AgentBlueprintResponse,
    AgentExecutionRequest,
    AgentExecutionResult,
)
from ai_flywheel.modules.agent_runtime.agent_factory.service import AgentFactory

router = APIRouter()
factory = AgentFactory()


@router.post("/", response_model=AgentBlueprintResponse)
async def create_agent(venture_id: str, data: AgentBlueprintCreate):
    return await factory.create_agent(venture_id, data)


@router.get("/", response_model=list[AgentBlueprintResponse])
async def list_agents(venture_id: str):
    return await factory.list_agents(venture_id)


@router.get("/{agent_id}", response_model=AgentBlueprintResponse)
async def get_agent(venture_id: str, agent_id: str):
    result = await factory.get_agent(venture_id, agent_id)
    if not result:
        raise HTTPException(404, "Agent not found")
    return result


@router.post("/execute", response_model=AgentExecutionResult)
async def execute_agent(venture_id: str, request: AgentExecutionRequest):
    return await factory.execute(venture_id, request)
