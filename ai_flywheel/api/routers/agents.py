"""Agent management and execution endpoints."""
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from typing import Any

from ai_flywheel.core.database import get_session
from ai_flywheel.core.llm import generate
from ai_flywheel.core.models import Venture
from ai_flywheel.modules.agent_runtime.agent_factory.intelligence import VentureIntelligenceStore
from ai_flywheel.modules.agent_runtime.agent_factory.models import AgentBlueprint
from ai_flywheel.modules.agent_runtime.agent_factory.schemas import (
    AgentBlueprintCreate,
    AgentBlueprintResponse,
    AgentExecutionRequest,
    AgentExecutionResult,
)
from ai_flywheel.modules.agent_runtime.agent_factory.service import AgentFactory
from ai_flywheel.modules.product_intelligence.offer_design.models import Offer
from ai_flywheel.modules.product_intelligence.venture_thesis.models import Thesis

router = APIRouter()
factory = AgentFactory()
intelligence_store = VentureIntelligenceStore()


# --- Schemas for new endpoints ---


class SuggestTaskRequest(BaseModel):
    agent_id: str
    venture_id: str


class SuggestTaskResponse(BaseModel):
    suggested_task: str
    context_summary: str


class RunNetworkRequest(BaseModel):
    venture_id: str


class NetworkResult(BaseModel):
    steps: list[dict[str, Any]]
    total_cost_usd: float
    total_duration_ms: float


# --- Existing endpoints ---


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


# --- New endpoints ---


@router.post("/suggest-task", response_model=SuggestTaskResponse)
async def suggest_task(request: SuggestTaskRequest):
    """Use LLM to suggest a task for an agent based on venture context."""
    venture_id = request.venture_id
    agent_id = request.agent_id

    # 1. Fetch agent blueprint
    async with get_session(venture_id) as session:
        stmt = select(AgentBlueprint).where(
            AgentBlueprint.id == agent_id,
            AgentBlueprint.venture_id == venture_id,
            AgentBlueprint.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        blueprint = result.scalar_one_or_none()
        if not blueprint:
            raise HTTPException(404, "Agent not found")

        agent_name = blueprint.name
        agent_type = blueprint.agent_type
        system_prompt = blueprint.system_prompt or "No system prompt defined."

    # 2. Fetch venture context
    context_parts = []

    # Thesis data
    async with get_session(venture_id) as session:
        stmt = select(Thesis).where(
            Thesis.venture_id == venture_id,
            Thesis.deleted_at.is_(None),
        ).limit(5)
        result = await session.execute(stmt)
        theses = result.scalars().all()
        if theses:
            thesis_info = "; ".join(
                f"{t.title}: {t.hypothesis}" for t in theses
            )
            context_parts.append(f"Theses: {thesis_info}")

    # Offer data
    async with get_session(venture_id) as session:
        stmt = select(Offer).where(
            Offer.venture_id == venture_id,
            Offer.deleted_at.is_(None),
        ).limit(5)
        result = await session.execute(stmt)
        offers = result.scalars().all()
        if offers:
            offer_info = "; ".join(
                f"{o.name} (ICP: {o.icp}, positioning: {o.positioning})" for o in offers
            )
            context_parts.append(f"Offers: {offer_info}")

    # Venture intelligence context
    try:
        intel_summary = await intelligence_store.get_context_summary(venture_id)
        if intel_summary and intel_summary != "No previous intelligence gathered yet.":
            context_parts.append(f"Previous Intelligence:\n{intel_summary}")
    except Exception:
        pass

    context_summary = " | ".join(context_parts) if context_parts else "No venture context available yet."

    # 3. Call LLM to generate suggestion
    messages = [
        {
            "role": "system",
            "content": (
                "You are a task suggestion engine for AI agents. Given an agent's role and "
                "venture context, suggest a single specific, actionable task the agent should "
                "perform next. Be concise and practical. Return only the task description."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Agent Name: {agent_name}\n"
                f"Agent Type: {agent_type}\n"
                f"Agent System Prompt: {system_prompt}\n\n"
                f"Venture Context:\n{context_summary}\n\n"
                "Suggest a specific actionable task for this agent."
            ),
        },
    ]

    response = await generate(
        messages=messages,
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=300,
        venture_id=venture_id,
        module_name="agent_suggest_task",
    )

    return SuggestTaskResponse(
        suggested_task=response.content.strip(),
        context_summary=context_summary,
    )


@router.post("/run-network", response_model=NetworkResult)
async def run_agent_network(request: RunNetworkRequest):
    """Run all agents in sequence: Research -> Analysis -> Writer. Each agent's output feeds the next."""
    venture_id = request.venture_id

    # 1. List all agents for the venture
    agents = await factory.list_agents(venture_id)
    if not agents:
        raise HTTPException(404, "No agents found for this venture")

    # 2. Sort agents: research first, then analysis, then writer/synthesis/execution
    def sort_key(agent: AgentBlueprintResponse) -> int:
        name_lower = (agent.name or "").lower()
        desc_lower = (agent.description or "").lower()
        type_lower = (agent.agent_type or "").lower()
        combined = f"{name_lower} {desc_lower} {type_lower}"

        if "research" in combined:
            return 0
        elif "analysis" in combined or "analy" in combined:
            return 1
        elif "writer" in combined or "synth" in combined or "execution" in combined:
            return 2
        return 3

    sorted_agents = sorted(agents, key=sort_key)

    # 3. Execute in sequence, passing previous output as context
    steps: list[dict[str, Any]] = []
    total_cost = 0.0
    total_duration = 0.0
    accumulated_context: dict[str, Any] = {}

    for agent in sorted_agents:
        task = (
            f"Execute your role as {agent.name}. "
            f"{'Use the following context from previous agents: ' + str(accumulated_context) if accumulated_context else 'You are the first agent in the pipeline.'}"
        )

        exec_request = AgentExecutionRequest(
            agent_id=agent.id,
            task=task,
            context=accumulated_context,
            require_approval=False,
        )

        try:
            result = await factory.execute(venture_id, exec_request)
            step_data = {
                "agent_id": agent.id,
                "agent_name": agent.name,
                "agent_type": agent.agent_type,
                "status": result.status,
                "output": result.output,
                "cost_usd": result.cost_usd,
                "duration_ms": result.duration_ms,
            }
            steps.append(step_data)
            total_cost += result.cost_usd
            total_duration += result.duration_ms

            # Feed output to next agent
            if result.output:
                accumulated_context[f"{agent.name}_output"] = result.output
        except Exception as e:
            steps.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "agent_type": agent.agent_type,
                "status": "failed",
                "output": str(e),
                "cost_usd": 0.0,
                "duration_ms": 0.0,
            })

    return NetworkResult(
        steps=steps,
        total_cost_usd=total_cost,
        total_duration_ms=total_duration,
    )


@router.get("/intelligence")
async def get_venture_intelligence(venture_id: str, limit: int = 20) -> list[dict]:
    """Get all stored agent outputs for a venture."""
    return await intelligence_store.get_outputs(venture_id, limit)


class NextActionRequest(BaseModel):
    venture_id: str


class NextActionResponse(BaseModel):
    recommendation: str
    context_used: str


@router.post("/next-action", response_model=NextActionResponse)
async def recommend_next_action(request: NextActionRequest):
    """AI recommends the next action based on venture state."""
    venture_id = request.venture_id

    # 1. Get intelligence summary
    intel_summary = await intelligence_store.get_context_summary(venture_id)

    # 2. Get venture context (thesis, offers)
    context_parts = [f"Intelligence:\n{intel_summary}"]

    async with get_session(venture_id) as session:
        stmt = select(Thesis).where(
            Thesis.venture_id == venture_id,
            Thesis.deleted_at.is_(None),
        ).limit(5)
        result = await session.execute(stmt)
        theses = result.scalars().all()
        if theses:
            thesis_info = "; ".join(f"{t.title}: {t.hypothesis}" for t in theses)
            context_parts.append(f"Theses: {thesis_info}")

    async with get_session(venture_id) as session:
        stmt = select(Offer).where(
            Offer.venture_id == venture_id,
            Offer.deleted_at.is_(None),
        ).limit(5)
        result = await session.execute(stmt)
        offers = result.scalars().all()
        if offers:
            offer_info = "; ".join(
                f"{o.name} (ICP: {o.icp}, positioning: {o.positioning})" for o in offers
            )
            context_parts.append(f"Offers: {offer_info}")

    context_used = "\n".join(context_parts)

    # 3. Call LLM for recommendation
    messages = [
        {
            "role": "system",
            "content": (
                "You are a venture strategy advisor. Based on the current state of the venture "
                "(intelligence gathered, theses, offers), recommend the single most impactful "
                "next action the founder should take. Be specific, actionable, and concise. "
                "Consider what has already been done and what gaps remain."
            ),
        },
        {
            "role": "user",
            "content": f"Venture State:\n{context_used}\n\nWhat should the founder do next?",
        },
    ]

    response = await generate(
        messages=messages,
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=400,
        venture_id=venture_id,
        module_name="next_action_advisor",
    )

    return NextActionResponse(
        recommendation=response.content.strip(),
        context_used=context_used[:500],
    )
