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
