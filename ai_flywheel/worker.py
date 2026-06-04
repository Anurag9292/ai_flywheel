"""Temporal worker entry point.

Runs the Temporal worker that executes workflows and activities.
Start with: python -m ai_flywheel.worker
"""

from __future__ import annotations

import asyncio

import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from ai_flywheel.core.config import settings
from ai_flywheel.workflows.sample import (
    SampleWorkflow,
    greet_activity,
    llm_activity,
)

logger = structlog.get_logger()


async def run_worker() -> None:
    """Connect to Temporal and run the worker."""
    logger.info(
        "worker_starting",
        host=settings.temporal_host,
        namespace=settings.temporal_namespace,
        task_queue=settings.temporal_task_queue,
    )

    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[SampleWorkflow],
        activities=[greet_activity, llm_activity],
        max_cached_workflows=200,
    )

    logger.info("worker_running", task_queue=settings.temporal_task_queue)
    await worker.run()


def main() -> None:
    """Entry point for the worker process."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
