"""Workflow execution endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ai_flywheel.core.tasks import get_temporal_client, start_workflow
from ai_flywheel.workflows.sample import SampleWorkflow, SampleWorkflowInput

router = APIRouter()


class StartWorkflowRequest(BaseModel):
    venture_id: str
    name: str
    prompt: str | None = None


class WorkflowStartedResponse(BaseModel):
    workflow_id: str
    status: str = "started"


@router.post("/sample", response_model=WorkflowStartedResponse)
async def start_sample_workflow(request: StartWorkflowRequest) -> WorkflowStartedResponse:
    """Start the sample workflow to test the execution spine."""
    import uuid

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
            "result": {
                "greeting": result.greeting,
                "llm_response": result.llm_response,
                "total_cost_usd": result.total_cost_usd,
                "steps_completed": result.steps_completed,
            },
        }
    except Exception as e:
        return {
            "workflow_id": workflow_id,
            "status": "error",
            "error": str(e),
        }
