"""Sample workflow to prove the execution spine works.

This workflow demonstrates:
- Multi-step execution via Activities
- Tracing integration (each step = a span)
- LLM call through the gateway with cost tracking
- Idempotency (safe to retry)
- Workflow surviving restarts (Temporal durability)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import structlog
    from ai_flywheel.core.llm import generate
    from ai_flywheel.core.traces import get_tracer

logger = structlog.get_logger()


@dataclass
class SampleWorkflowInput:
    """Input for the sample workflow."""

    venture_id: str
    name: str
    prompt: str | None = None


@dataclass
class SampleWorkflowResult:
    """Result from the sample workflow."""

    greeting: str
    llm_response: str | None = None
    total_cost_usd: float = 0.0
    steps_completed: int = 0


@activity.defn
async def greet_activity(name: str) -> str:
    """Simple activity to demonstrate execution."""
    tracer = get_tracer()
    async with tracer.span("sample", "greet", input_data={"name": name}):
        greeting = f"Hello, {name}! The execution spine is working."
        logger.info("greet_activity", name=name)
        return greeting


@activity.defn
async def llm_activity(prompt: str, venture_id: str) -> dict:
    """Activity that makes an LLM call through the gateway.

    Demonstrates:
    - LLM Gateway usage from an activity
    - Idempotency via activity ID
    - Cost tracking
    """
    activity_id = activity.info().activity_id
    tracer = get_tracer()
    tracer.set_venture_context(venture_id)

    async with tracer.span(
        "sample", "llm_call", input_data={"prompt": prompt[:100]}
    ) as span:
        response = await generate(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            idempotency_key=activity_id,
            venture_id=venture_id,
            module_name="sample_workflow",
        )

        span.set_cost(
            cost_usd=response.cost_usd,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            model=response.model,
        )

        return {
            "content": response.content,
            "cost_usd": response.cost_usd,
            "tokens_input": response.tokens_input,
            "tokens_output": response.tokens_output,
            "model": response.model,
            "cached": response.cached,
        }


@workflow.defn
class SampleWorkflow:
    """Sample workflow proving the execution spine.

    Steps:
    1. Greet (simple activity)
    2. Optional LLM call (demonstrates gateway + cost tracking)
    3. Return aggregated results
    """

    @workflow.run
    async def run(self, input: SampleWorkflowInput) -> SampleWorkflowResult:
        # Step 1: Simple greeting
        greeting = await workflow.execute_activity(
            greet_activity,
            input.name,
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Step 2: Optional LLM call
        llm_response = None
        total_cost = 0.0

        if input.prompt:
            result = await workflow.execute_activity(
                llm_activity,
                args=[input.prompt, input.venture_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(maximum_attempts=3),
            )
            llm_response = result["content"]
            total_cost = result["cost_usd"]

        return SampleWorkflowResult(
            greeting=greeting,
            llm_response=llm_response,
            total_cost_usd=total_cost,
            steps_completed=2 if input.prompt else 1,
        )
