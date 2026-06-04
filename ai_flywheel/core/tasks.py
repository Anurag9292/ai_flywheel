"""Task Runtime — Temporal.io wrapper for durable workflow execution.

All long-running operations execute as Temporal workflows. This module provides:
- Client connection management
- Workflow submission and status tracking
- Activity patterns with idempotency
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import structlog
from temporalio.client import Client

from ai_flywheel.core.config import settings

logger = structlog.get_logger()

# Global client reference
_temporal_client: Client | None = None


async def get_temporal_client() -> Client:
    """Get or create the Temporal client connection."""
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
        logger.info(
            "temporal_connected",
            host=settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
    return _temporal_client


async def close_temporal_client() -> None:
    """Close the Temporal client connection."""
    global _temporal_client
    if _temporal_client:
        _temporal_client = None
        logger.info("temporal_disconnected")


async def start_workflow(
    workflow_class: Any,
    arg: Any,
    workflow_id: str,
    task_queue: str | None = None,
    execution_timeout: timedelta | None = None,
) -> str:
    """Start a Temporal workflow.

    Args:
        workflow_class: The workflow class (decorated with @workflow.defn)
        arg: Argument to pass to the workflow
        workflow_id: Unique identifier for this execution
        task_queue: Override default task queue
        execution_timeout: Maximum workflow execution time

    Returns:
        The workflow run ID
    """
    client = await get_temporal_client()
    handle = await client.start_workflow(
        workflow_class.run,
        arg,
        id=workflow_id,
        task_queue=task_queue or settings.temporal_task_queue,
        execution_timeout=execution_timeout or timedelta(hours=24),
    )
    logger.info(
        "workflow_started",
        workflow_id=workflow_id,
        workflow_type=workflow_class.__name__,
        task_queue=task_queue or settings.temporal_task_queue,
    )
    return handle.result_run_id


async def get_workflow_result(workflow_id: str, timeout: timedelta | None = None) -> Any:
    """Wait for a workflow to complete and return its result."""
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    return await handle.result()


async def signal_workflow(workflow_id: str, signal_name: str, arg: Any = None) -> None:
    """Send a signal to a running workflow."""
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal(signal_name, arg)
    logger.info("workflow_signaled", workflow_id=workflow_id, signal=signal_name)


async def cancel_workflow(workflow_id: str) -> None:
    """Cancel a running workflow."""
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    await handle.cancel()
    logger.info("workflow_cancelled", workflow_id=workflow_id)
