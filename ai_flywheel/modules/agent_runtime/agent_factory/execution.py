"""Temporal activities and workflows for agent execution.

This module defines the durable execution primitives:
- execute_agent_activity: Single agent LLM call (the atomic unit)
- SingleAgentWorkflow: One agent with timeout + retry
- ChainAgentWorkflow: Sequential chain (output feeds into next)
- ParallelAgentWorkflow: Fan-out, merge results
- ApprovalAgentWorkflow: Execute, pause for human signal, then return
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import structlog

    from ai_flywheel.core.llm import generate
    from ai_flywheel.core.traces import get_tracer

logger = structlog.get_logger()


# --- Dataclass inputs/outputs (Temporal serialization requirement) ---


@dataclass
class AgentActivityInput:
    """Input for the execute_agent_activity."""

    agent_config: dict[str, Any]
    task: str
    context: dict[str, Any]
    venture_id: str
    execution_id: str = ""


@dataclass
class AgentActivityOutput:
    """Output from execute_agent_activity."""

    content: str
    cost_usd: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    model: str = ""
    status: str = "completed"
    error: str | None = None


@dataclass
class SingleWorkflowInput:
    """Input for SingleAgentWorkflow."""

    agent_config: dict[str, Any]
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    venture_id: str = ""
    execution_id: str = ""


@dataclass
class ChainWorkflowInput:
    """Input for ChainAgentWorkflow."""

    agent_config: dict[str, Any]
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    venture_id: str = ""
    execution_id: str = ""


@dataclass
class ParallelWorkflowInput:
    """Input for ParallelAgentWorkflow."""

    agent_config: dict[str, Any]
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    venture_id: str = ""
    execution_id: str = ""


@dataclass
class ApprovalWorkflowInput:
    """Input for ApprovalAgentWorkflow."""

    agent_config: dict[str, Any]
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    venture_id: str = ""
    execution_id: str = ""


# --- Activity ---


@activity.defn
async def execute_agent_activity(input: AgentActivityInput) -> AgentActivityOutput:
    """Execute a single agent — one LLM call with the agent's config.

    This is the atomic execution unit. Temporal handles retries and timeouts.
    """
    agent_config = input.agent_config
    task = input.task
    context = input.context
    venture_id = input.venture_id

    tracer = get_tracer()
    tracer.set_venture_context(venture_id)
    activity_id = activity.info().activity_id

    # Build messages
    messages: list[dict[str, str]] = []

    system_prompt = agent_config.get("system_prompt")
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    user_content = task
    if context:
        context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
        user_content = f"{task}\n\nContext:\n{context_str}"
    messages.append({"role": "user", "content": user_content})

    async with tracer.span(
        "agent_factory",
        "execute_agent_activity",
        input_data={"agent_name": agent_config.get("name"), "task": task[:200]},
    ) as span:
        try:
            response = await generate(
                messages=messages,
                model=agent_config.get("model", "gpt-4o-mini"),
                temperature=agent_config.get("temperature", 0.7),
                max_tokens=agent_config.get("max_tokens"),
                idempotency_key=activity_id,
                venture_id=venture_id,
                module_name="agent_factory",
            )

            span.set_cost(
                cost_usd=response.cost_usd,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                model=response.model,
            )

            logger.info(
                "agent_activity_completed",
                agent_name=agent_config.get("name"),
                model=response.model,
                cost_usd=response.cost_usd,
                venture_id=venture_id,
            )

            return AgentActivityOutput(
                content=response.content,
                cost_usd=response.cost_usd,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                model=response.model,
                status="completed",
            )
        except Exception as e:
            logger.error(
                "agent_activity_failed",
                agent_name=agent_config.get("name"),
                error=str(e),
                venture_id=venture_id,
            )
            return AgentActivityOutput(
                content="",
                status="failed",
                error=str(e),
            )


# --- Workflows ---


@workflow.defn
class SingleAgentWorkflow:
    """Execute a single agent with configurable timeout and retry policy.

    This is the simplest workflow — one activity call with Temporal durability.
    """

    @workflow.run
    async def run(self, input: SingleWorkflowInput) -> dict[str, Any]:
        agent_config = input.agent_config
        timeout_seconds = agent_config.get("timeout_seconds", 120)
        retry_policy_config = agent_config.get("retry_policy", {})

        retry_policy = workflow.RetryPolicy(
            maximum_attempts=retry_policy_config.get("maximum_attempts", 3),
            backoff_coefficient=retry_policy_config.get("backoff_coefficient", 2.0),
        )

        activity_input = AgentActivityInput(
            agent_config=agent_config,
            task=input.task,
            context=input.context,
            venture_id=input.venture_id,
            execution_id=input.execution_id,
        )

        result = await workflow.execute_activity(
            execute_agent_activity,
            activity_input,
            start_to_close_timeout=timedelta(seconds=timeout_seconds),
            retry_policy=retry_policy,
        )

        return {
            "status": result.status,
            "output": result.content,
            "cost_usd": result.cost_usd,
            "tokens_input": result.tokens_input,
            "tokens_output": result.tokens_output,
        }


@workflow.defn
class ChainAgentWorkflow:
    """Sequential chain of agent executions — output of one feeds into next.

    The chain is defined by the `tools` field in the agent config, where each
    tool entry represents a step with its own system_prompt override. If no
    chain steps are defined, runs the agent once as a single step.
    """

    @workflow.run
    async def run(self, input: ChainWorkflowInput) -> dict[str, Any]:
        agent_config = input.agent_config
        timeout_seconds = agent_config.get("timeout_seconds", 120)
        retry_policy_config = agent_config.get("retry_policy", {})

        retry_policy = workflow.RetryPolicy(
            maximum_attempts=retry_policy_config.get("maximum_attempts", 3),
            backoff_coefficient=retry_policy_config.get("backoff_coefficient", 2.0),
        )

        # Chain steps from tools config, or single execution
        chain_steps = agent_config.get("tools", [])
        if not chain_steps:
            chain_steps = [agent_config.get("name", "default")]

        current_task = input.task
        current_context = dict(input.context)
        total_cost = 0.0
        total_tokens_input = 0
        total_tokens_output = 0
        last_output = ""

        for step_index, _step in enumerate(chain_steps):
            # Each step uses the same base config but with the previous output as context
            step_context = dict(current_context)
            if step_index > 0:
                step_context["previous_step_output"] = last_output

            activity_input = AgentActivityInput(
                agent_config=agent_config,
                task=current_task,
                context=step_context,
                venture_id=input.venture_id,
                execution_id=f"{input.execution_id}-step-{step_index}",
            )

            result = await workflow.execute_activity(
                execute_agent_activity,
                activity_input,
                start_to_close_timeout=timedelta(seconds=timeout_seconds),
                retry_policy=retry_policy,
            )

            if result.status == "failed":
                return {
                    "status": "failed",
                    "output": result.error or "Chain step failed",
                    "cost_usd": total_cost,
                    "tokens_input": total_tokens_input,
                    "tokens_output": total_tokens_output,
                }

            last_output = result.content
            total_cost += result.cost_usd
            total_tokens_input += result.tokens_input
            total_tokens_output += result.tokens_output

            # For chain, the next step's task becomes the previous output
            current_task = last_output

        return {
            "status": "completed",
            "output": last_output,
            "cost_usd": total_cost,
            "tokens_input": total_tokens_input,
            "tokens_output": total_tokens_output,
        }


@workflow.defn
class ParallelAgentWorkflow:
    """Fan-out multiple agent executions in parallel, merge results.

    Splits the task across parallel branches (one per tool entry) and combines
    their outputs into a single merged result.
    """

    @workflow.run
    async def run(self, input: ParallelWorkflowInput) -> dict[str, Any]:
        agent_config = input.agent_config
        timeout_seconds = agent_config.get("timeout_seconds", 120)
        retry_policy_config = agent_config.get("retry_policy", {})

        retry_policy = workflow.RetryPolicy(
            maximum_attempts=retry_policy_config.get("maximum_attempts", 3),
            backoff_coefficient=retry_policy_config.get("backoff_coefficient", 2.0),
        )

        # Parallel branches from tools config
        branches = agent_config.get("tools", [])
        if not branches:
            branches = ["default"]

        # Fan-out: execute all branches concurrently
        tasks = []
        for branch_index, _branch in enumerate(branches):
            activity_input = AgentActivityInput(
                agent_config=agent_config,
                task=input.task,
                context=input.context,
                venture_id=input.venture_id,
                execution_id=f"{input.execution_id}-branch-{branch_index}",
            )

            task = workflow.execute_activity(
                execute_agent_activity,
                activity_input,
                start_to_close_timeout=timedelta(seconds=timeout_seconds),
                retry_policy=retry_policy,
            )
            tasks.append(task)

        # Wait for all branches to complete
        results = await asyncio.gather(*tasks)

        # Merge results
        total_cost = 0.0
        total_tokens_input = 0
        total_tokens_output = 0
        outputs = []
        all_completed = True

        for result in results:
            total_cost += result.cost_usd
            total_tokens_input += result.tokens_input
            total_tokens_output += result.tokens_output
            outputs.append(result.content)
            if result.status != "completed":
                all_completed = False

        merged_output = "\n\n---\n\n".join(outputs)

        return {
            "status": "completed" if all_completed else "partial",
            "output": merged_output,
            "cost_usd": total_cost,
            "tokens_input": total_tokens_input,
            "tokens_output": total_tokens_output,
            "branch_count": len(results),
        }


@workflow.defn
class ApprovalAgentWorkflow:
    """Execute an agent then pause for human approval before returning result.

    Flow:
    1. Execute the agent activity
    2. Store the result
    3. Pause (wait_condition) until approve/reject signal arrives
    4. Return approved result or rejection
    """

    def __init__(self) -> None:
        self._approval_decision: str | None = None  # "approve" or "reject"
        self._reviewer_comment: str = ""
        self._agent_output: AgentActivityOutput | None = None

    @workflow.signal
    async def approve(self, comment: str = "") -> None:
        """Signal to approve the agent's output."""
        self._approval_decision = "approve"
        self._reviewer_comment = comment

    @workflow.signal
    async def reject(self, comment: str = "") -> None:
        """Signal to reject the agent's output."""
        self._approval_decision = "reject"
        self._reviewer_comment = comment

    @workflow.run
    async def run(self, input: ApprovalWorkflowInput) -> dict[str, Any]:
        agent_config = input.agent_config
        timeout_seconds = agent_config.get("timeout_seconds", 120)
        retry_policy_config = agent_config.get("retry_policy", {})

        retry_policy = workflow.RetryPolicy(
            maximum_attempts=retry_policy_config.get("maximum_attempts", 3),
            backoff_coefficient=retry_policy_config.get("backoff_coefficient", 2.0),
        )

        # Step 1: Execute the agent
        activity_input = AgentActivityInput(
            agent_config=agent_config,
            task=input.task,
            context=input.context,
            venture_id=input.venture_id,
            execution_id=input.execution_id,
        )

        self._agent_output = await workflow.execute_activity(
            execute_agent_activity,
            activity_input,
            start_to_close_timeout=timedelta(seconds=timeout_seconds),
            retry_policy=retry_policy,
        )

        # If the agent itself failed, no point waiting for approval
        if self._agent_output.status == "failed":
            return {
                "status": "failed",
                "output": self._agent_output.error or "Agent execution failed",
                "cost_usd": self._agent_output.cost_usd,
                "tokens_input": self._agent_output.tokens_input,
                "tokens_output": self._agent_output.tokens_output,
            }

        # Step 2: Wait for human approval signal
        # This pauses the workflow until approve() or reject() signal is received
        await workflow.wait_condition(lambda: self._approval_decision is not None)

        # Step 3: Return result based on decision
        if self._approval_decision == "approve":
            return {
                "status": "completed",
                "output": self._agent_output.content,
                "cost_usd": self._agent_output.cost_usd,
                "tokens_input": self._agent_output.tokens_input,
                "tokens_output": self._agent_output.tokens_output,
                "approval": "approved",
                "reviewer_comment": self._reviewer_comment,
            }
        else:
            return {
                "status": "rejected",
                "output": self._agent_output.content,
                "cost_usd": self._agent_output.cost_usd,
                "tokens_input": self._agent_output.tokens_input,
                "tokens_output": self._agent_output.tokens_output,
                "approval": "rejected",
                "reviewer_comment": self._reviewer_comment,
            }
