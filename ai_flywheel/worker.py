"""Temporal worker entry point.

Runs the Temporal worker that executes all platform workflows and activities.
Start with: python -m ai_flywheel.worker
"""

from __future__ import annotations

import asyncio

import structlog
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from ai_flywheel.core.config import settings

# Phase 0: Sample workflow
from ai_flywheel.workflows.sample import (
    SampleWorkflow,
    greet_activity,
    llm_activity,
)

# Phase 1: Agent Factory workflows and activities
from ai_flywheel.modules.agent_runtime.agent_factory.execution import (
    ApprovalAgentWorkflow,
    ChainAgentWorkflow,
    ParallelAgentWorkflow,
    SingleAgentWorkflow,
    execute_agent_activity,
)

# Phase 2: Venture Lifecycle Orchestration
from ai_flywheel.workflows.venture_lifecycle import (
    VentureLifecycleWorkflow,
    thesis_stage_activity,
    discovery_stage_activity,
    market_stage_activity,
    offer_stage_activity,
    blueprint_stage_activity,
    agent_setup_activity,
    kill_check_activity,
)

logger = structlog.get_logger()

# All workflows the worker can execute
ALL_WORKFLOWS = [
    SampleWorkflow,
    SingleAgentWorkflow,
    ChainAgentWorkflow,
    ParallelAgentWorkflow,
    ApprovalAgentWorkflow,
    VentureLifecycleWorkflow,
]

# All activities the worker can execute
ALL_ACTIVITIES = [
    greet_activity,
    llm_activity,
    execute_agent_activity,
    thesis_stage_activity,
    discovery_stage_activity,
    market_stage_activity,
    offer_stage_activity,
    blueprint_stage_activity,
    agent_setup_activity,
    kill_check_activity,
]


async def run_worker() -> None:
    """Connect to Temporal and run the worker."""
    logger.info(
        "worker_starting",
        host=settings.temporal_host,
        namespace=settings.temporal_namespace,
        task_queue=settings.temporal_task_queue,
        workflows=len(ALL_WORKFLOWS),
        activities=len(ALL_ACTIVITIES),
    )

    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=ALL_WORKFLOWS,
        activities=ALL_ACTIVITIES,
        max_cached_workflows=200,
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules(
                "ai_flywheel",
            )
        ),
    )

    logger.info("worker_running", task_queue=settings.temporal_task_queue)
    await worker.run()


def main() -> None:
    """Entry point for the worker process."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
