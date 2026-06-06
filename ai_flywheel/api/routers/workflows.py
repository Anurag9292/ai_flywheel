"""Workflow execution endpoints."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from ai_flywheel.core.tasks import get_temporal_client, signal_workflow, start_workflow
from ai_flywheel.workflows.sample import SampleWorkflow, SampleWorkflowInput
from ai_flywheel.workflows.venture_lifecycle import (
    VentureLifecycleInput,
    VentureLifecycleWorkflow,
)

router = APIRouter()

# In-memory job store for graph deployments
_graph_jobs: dict[str, dict] = {}


class StartWorkflowRequest(BaseModel):
    venture_id: str
    name: str
    prompt: str | None = None


class WorkflowStartedResponse(BaseModel):
    workflow_id: str
    status: str = "started"


# --- Venture Lifecycle ---


class LifecycleRequest(BaseModel):
    venture_id: str
    venture_name: str
    domain: str
    initial_hypothesis: str
    assumptions: list[str] = []
    kill_signals: list[str] = []


class SuggestLifecycleRequest(BaseModel):
    venture_name: str
    domain: str


class SuggestLifecycleResponse(BaseModel):
    hypothesis: str
    assumptions: list[str]
    kill_signals: list[str]


@router.post("/lifecycle/suggest", response_model=SuggestLifecycleResponse)
async def suggest_lifecycle_fields(request: SuggestLifecycleRequest) -> SuggestLifecycleResponse:
    """Use LLM to generate hypothesis, assumptions, and kill signals from venture name/domain."""
    from ai_flywheel.core.llm import generate

    prompt = f"""You are a venture validation expert. Given a venture idea, generate structured validation inputs.

Venture: {request.venture_name}
Domain: {request.domain}

Generate:
1. A structured hypothesis in the format: "We believe [ICP] will pay [price] for [solution] because [pain]. Disproven if [condition]."
2. 4-6 testable assumptions that must be true for this venture to succeed
3. 3-4 kill signals that would indicate this venture should be abandoned

Respond in this exact JSON format:
{{
  "hypothesis": "...",
  "assumptions": ["...", "...", "...", "...", "..."],
  "kill_signals": ["...", "...", "..."]
}}

Respond ONLY with the JSON, no other text."""

    response = await generate(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=800,
        module_name="lifecycle_suggest",
    )

    import json
    try:
        content = response.content
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(content)
        return SuggestLifecycleResponse(
            hypothesis=data.get("hypothesis", ""),
            assumptions=data.get("assumptions", []),
            kill_signals=data.get("kill_signals", []),
        )
    except (json.JSONDecodeError, KeyError):
        # Fallback
        return SuggestLifecycleResponse(
            hypothesis=f"We believe target customers in {request.domain} will pay for {request.venture_name} because they have an unmet need.",
            assumptions=[
                "Target users experience this pain frequently",
                "They currently have no adequate solution",
                "They have budget authority to purchase",
                "The market is large enough to sustain a business",
            ],
            kill_signals=[
                "Fewer than 3/10 interviews confirm the pain",
                "Landing page converts below 2%",
                "Willingness to pay is under the break-even price",
            ],
        )


# In-memory workflow registry (per venture) — in production use DB
_active_workflows: dict[str, str] = {}  # venture_id -> workflow_id


@router.post("/lifecycle", response_model=WorkflowStartedResponse)
async def start_lifecycle_workflow(request: LifecycleRequest) -> WorkflowStartedResponse:
    """Start the venture lifecycle orchestration workflow.

    Runs through: Thesis → Discovery → Market → Offer with kill gates.
    """
    workflow_id = f"lifecycle-{request.venture_id}-{uuid.uuid4().hex[:8]}"

    await start_workflow(
        workflow_class=VentureLifecycleWorkflow,
        arg=VentureLifecycleInput(
            venture_id=request.venture_id,
            venture_name=request.venture_name,
            domain=request.domain,
            initial_hypothesis=request.initial_hypothesis,
            assumptions=request.assumptions,
            kill_signals=request.kill_signals,
        ),
        workflow_id=workflow_id,
    )

    _active_workflows[request.venture_id] = workflow_id
    return WorkflowStartedResponse(workflow_id=workflow_id)


@router.get("/venture/{venture_id}/active")
async def get_active_workflow(venture_id: str) -> dict:
    """Get the active lifecycle workflow for a venture."""
    workflow_id = _active_workflows.get(venture_id)
    if not workflow_id:
        return {"venture_id": venture_id, "workflow_id": None, "status": "none"}

    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    try:
        status = await handle.query(VentureLifecycleWorkflow.get_status)
        return {"venture_id": venture_id, "workflow_id": workflow_id, **status}
    except Exception as e:
        return {"venture_id": venture_id, "workflow_id": workflow_id, "status": "completed_or_error", "error": str(e)}


@router.post("/{workflow_id}/approve")
async def approve_workflow_stage(workflow_id: str) -> dict:
    """Send approval signal to a waiting lifecycle workflow."""
    await signal_workflow(workflow_id, "approve_stage")
    return {"workflow_id": workflow_id, "signal": "approve_stage", "status": "sent"}


@router.post("/{workflow_id}/kill")
async def kill_workflow(workflow_id: str, reason: str = "Manual kill") -> dict:
    """Send kill signal to terminate a lifecycle workflow."""
    await signal_workflow(workflow_id, "kill_venture", reason)
    return {"workflow_id": workflow_id, "signal": "kill_venture", "reason": reason, "status": "sent"}


@router.post("/{workflow_id}/transcript-analyzed")
async def transcript_analyzed(workflow_id: str, count: int = 1) -> dict:
    """Signal that a transcript has been analyzed during discovery stage."""
    await signal_workflow(workflow_id, "transcript_analyzed", count)
    return {"workflow_id": workflow_id, "signal": "transcript_analyzed", "count": count, "status": "sent"}


@router.post("/{workflow_id}/complete-discovery")
async def complete_discovery(workflow_id: str) -> dict:
    """Manually complete the discovery stage and proceed to market."""
    await signal_workflow(workflow_id, "complete_discovery")
    return {"workflow_id": workflow_id, "signal": "complete_discovery", "status": "sent"}


@router.get("/{workflow_id}/status")
async def get_workflow_status(workflow_id: str) -> dict:
    """Query current status of a lifecycle workflow."""
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    try:
        status = await handle.query(VentureLifecycleWorkflow.get_status)
        return {"workflow_id": workflow_id, **status}
    except Exception as e:
        return {"workflow_id": workflow_id, "error": str(e)}


# --- Sample Workflow ---


@router.post("/sample", response_model=WorkflowStartedResponse)
async def start_sample_workflow(request: StartWorkflowRequest) -> WorkflowStartedResponse:
    """Start the sample workflow to test the execution spine."""
    workflow_id = f"sample-{uuid.uuid4()}"

    await start_workflow(
        workflow_class=SampleWorkflow,
        arg=SampleWorkflowInput(
            venture_id=request.venture_id,
            name=request.name,
            prompt=request.prompt,
        ),
        workflow_id=workflow_id,
    )

    return WorkflowStartedResponse(workflow_id=workflow_id)


# --- Generic Result ---


@router.get("/{workflow_id}/result")
async def get_workflow_result(workflow_id: str) -> dict:
    """Get the result of a completed workflow."""
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    try:
        result = await handle.result()
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "result": result if isinstance(result, dict) else str(result),
        }
    except Exception as e:
        return {
            "workflow_id": workflow_id,
            "status": "error",
            "error": str(e),
        }


# --- Deploy Graph ---


class DeployGraphRequest(BaseModel):
    venture_id: str
    name: str
    steps: list[dict]
    edges: list[dict]
    execution_order: list[str]


@router.post("/deploy-graph")
async def deploy_graph_workflow(request: DeployGraphRequest) -> dict:
    """Deploy a compiled graph as agent executions.

    For each step in execution_order that is an 'agent' type node,
    creates or looks up the agent and executes them in order with
    context flowing between them.
    """
    job_id = str(uuid.uuid4())
    _graph_jobs[job_id] = {"status": "running", "steps": [], "venture_id": request.venture_id}

    # Run in background
    asyncio.create_task(_execute_graph(job_id, request))

    return {"job_id": job_id, "status": "running"}


@router.get("/deploy-graph/{job_id}")
async def get_graph_deploy_result(job_id: str) -> dict:
    """Poll for graph deployment results."""
    job = _graph_jobs.get(job_id)
    if not job:
        return {"status": "not_found"}
    return job


async def _execute_graph(job_id: str, request: DeployGraphRequest):
    """Background task that executes graph nodes in topological order."""
    from ai_flywheel.modules.agent_runtime.agent_factory.schemas import (
        AgentBlueprintCreate,
        AgentExecutionRequest,
    )
    from ai_flywheel.modules.agent_runtime.agent_factory.service import AgentFactory

    factory = AgentFactory()

    try:
        venture_id = request.venture_id
        steps_by_id = {step["id"]: step for step in request.steps}
        steps_executed = []
        previous_output = ""
        total_cost = 0.0
        total_duration = 0.0

        for node_id in request.execution_order:
            step_def = steps_by_id.get(node_id)
            if not step_def or step_def.get("type") != "agent":
                continue

            label = step_def.get("label", "Agent")
            model = step_def.get("model", "gpt-4o-mini")

            # Look up existing agent or create one
            existing_agents = await factory.list_agents(venture_id)
            agent = next((a for a in existing_agents if a.name == label), None)

            if not agent:
                agent = await factory.create_agent(
                    venture_id,
                    AgentBlueprintCreate(
                        name=label,
                        description=f"Graph-deployed agent: {label}",
                        agent_type="single",
                        model=model,
                        system_prompt=f"You are {label}. Execute your task based on the provided context.",
                    ),
                )

            # Build task with context from previous step
            task_text = f"Execute your role as '{label}' for workflow '{request.name}'."
            if previous_output:
                task_text += f"\n\nContext from previous step:\n{previous_output[:2000]}"

            exec_request = AgentExecutionRequest(
                agent_id=agent.id,
                task=task_text,
                context={"previous_output": previous_output[:2000]} if previous_output else {},
            )

            result = await factory.execute(venture_id, exec_request)

            step_result = {
                "node_id": node_id,
                "agent_name": label,
                "agent_id": agent.id,
                "status": result.status,
                "output": result.output or "",
                "cost_usd": result.cost_usd,
                "duration_ms": result.duration_ms,
            }
            steps_executed.append(step_result)
            total_cost += result.cost_usd
            total_duration += result.duration_ms

            if result.output:
                previous_output = result.output

            # Update job progress
            _graph_jobs[job_id] = {
                "status": "running",
                "steps": steps_executed,
                "total_cost_usd": total_cost,
                "total_duration_ms": total_duration,
                "progress": f"{len(steps_executed)} agents executed",
            }

        _graph_jobs[job_id] = {
            "status": "completed",
            "steps": steps_executed,
            "total_cost_usd": total_cost,
            "total_duration_ms": total_duration,
        }
    except Exception as e:
        _graph_jobs[job_id] = {
            "status": "error",
            "error": str(e),
            "steps": _graph_jobs.get(job_id, {}).get("steps", []),
        }
