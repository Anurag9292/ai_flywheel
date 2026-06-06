"""Workflow execution endpoints."""

from __future__ import annotations

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
