"""Agent Factory — CRUD + execution orchestration for agent blueprints.

The AgentFactory is the primary interface for managing and running agents.
It handles:
- Blueprint CRUD (create, read, update, list)
- Execution dispatch (routes to the correct Temporal workflow based on agent_type)
- Event emission for observability
- Cost tracking integration
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.llm import generate
from ai_flywheel.core.traces import get_tracer

from .models import AgentBlueprint
from .schemas import (
    AgentBlueprintCreate,
    AgentBlueprintResponse,
    AgentBlueprintUpdate,
    AgentExecutionRequest,
    AgentExecutionResult,
)

logger = structlog.get_logger()


class AgentFactory:
    """Factory for creating, managing, and executing agent blueprints.

    Usage:
        factory = AgentFactory()
        agent = await factory.create_agent(venture_id, AgentBlueprintCreate(...))
        result = await factory.execute(venture_id, AgentExecutionRequest(...))
    """

    def __init__(self) -> None:
        self._event_bus = get_event_bus()
        self._tracer = get_tracer()

    async def create_agent(
        self, venture_id: str, data: AgentBlueprintCreate
    ) -> AgentBlueprintResponse:
        """Create a new agent blueprint."""
        async with get_session(venture_id) as session:
            blueprint = AgentBlueprint(
                venture_id=venture_id,
                name=data.name,
                description=data.description,
                agent_type=data.agent_type,
                model=data.model,
                system_prompt=data.system_prompt,
                tools=data.tools,
                memory_tiers=data.memory_tiers,
                max_tokens=data.max_tokens,
                temperature=data.temperature,
                timeout_seconds=data.timeout_seconds,
                retry_policy=data.retry_policy,
            )
            session.add(blueprint)
            await session.flush()

            response = AgentBlueprintResponse.model_validate(blueprint)

        await self._event_bus.publish(
            event_type="agent.created",
            source_module="agent_factory",
            payload={
                "agent_id": response.id,
                "name": response.name,
                "agent_type": response.agent_type,
            },
            venture_id=venture_id,
        )

        logger.info(
            "agent_created",
            agent_id=response.id,
            name=response.name,
            agent_type=response.agent_type,
            venture_id=venture_id,
        )
        return response

    async def get_agent(
        self, venture_id: str, agent_id: str
    ) -> AgentBlueprintResponse:
        """Get an agent blueprint by ID."""
        async with get_session(venture_id) as session:
            stmt = select(AgentBlueprint).where(
                AgentBlueprint.id == agent_id,
                AgentBlueprint.venture_id == venture_id,
                AgentBlueprint.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            blueprint = result.scalar_one()
            return AgentBlueprintResponse.model_validate(blueprint)

    async def get_agent_by_name(
        self, venture_id: str, name: str
    ) -> AgentBlueprintResponse:
        """Get an agent blueprint by name within a venture."""
        async with get_session(venture_id) as session:
            stmt = select(AgentBlueprint).where(
                AgentBlueprint.name == name,
                AgentBlueprint.venture_id == venture_id,
                AgentBlueprint.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            blueprint = result.scalar_one()
            return AgentBlueprintResponse.model_validate(blueprint)

    async def list_agents(
        self, venture_id: str, agent_type: str | None = None
    ) -> list[AgentBlueprintResponse]:
        """List all active agent blueprints for a venture."""
        async with get_session(venture_id) as session:
            stmt = select(AgentBlueprint).where(
                AgentBlueprint.venture_id == venture_id,
                AgentBlueprint.deleted_at.is_(None),
                AgentBlueprint.is_active.is_(True),
            )
            if agent_type:
                stmt = stmt.where(AgentBlueprint.agent_type == agent_type)
            stmt = stmt.order_by(AgentBlueprint.created_at.desc())

            result = await session.execute(stmt)
            blueprints = result.scalars().all()
            return [AgentBlueprintResponse.model_validate(bp) for bp in blueprints]

    async def update_agent(
        self, venture_id: str, agent_id: str, data: AgentBlueprintUpdate
    ) -> AgentBlueprintResponse:
        """Update an agent blueprint. Increments version on changes."""
        async with get_session(venture_id) as session:
            stmt = select(AgentBlueprint).where(
                AgentBlueprint.id == agent_id,
                AgentBlueprint.venture_id == venture_id,
                AgentBlueprint.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            blueprint = result.scalar_one()

            # Apply only provided fields
            update_data = data.model_dump(exclude_unset=True)
            if update_data:
                for field, value in update_data.items():
                    setattr(blueprint, field, value)
                blueprint.version += 1

            await session.flush()
            response = AgentBlueprintResponse.model_validate(blueprint)

        await self._event_bus.publish(
            event_type="agent.updated",
            source_module="agent_factory",
            payload={"agent_id": response.id, "name": response.name, "version": response.version},
            venture_id=venture_id,
        )

        logger.info(
            "agent_updated",
            agent_id=response.id,
            name=response.name,
            version=response.version,
            venture_id=venture_id,
        )
        return response

    async def execute(
        self, venture_id: str, request: AgentExecutionRequest
    ) -> AgentExecutionResult:
        """Execute an agent — the core method.

        Resolves the blueprint, builds messages, calls LLM, tracks cost, emits events.
        For approval workflows, starts a Temporal workflow that pauses for human signal.
        """
        execution_id = str(uuid.uuid4())
        trace_id = self._tracer.start_trace(venture_id)
        start_time = time.time()

        # Resolve blueprint
        if request.agent_id:
            blueprint = await self.get_agent(venture_id, request.agent_id)
        elif request.agent_name:
            blueprint = await self.get_agent_by_name(venture_id, request.agent_name)
        else:
            raise ValueError("Either agent_id or agent_name must be provided")

        await self._event_bus.publish(
            event_type="agent.execution.started",
            source_module="agent_factory",
            payload={
                "execution_id": execution_id,
                "agent_id": blueprint.id,
                "agent_name": blueprint.name,
                "task": request.task[:200],
                "require_approval": request.require_approval,
            },
            venture_id=venture_id,
            correlation_id=execution_id,
        )

        try:
            # For approval workflows, delegate to Temporal
            if request.require_approval:
                return await self._execute_with_approval(
                    venture_id=venture_id,
                    execution_id=execution_id,
                    blueprint=blueprint,
                    request=request,
                    trace_id=trace_id,
                    start_time=start_time,
                )

            # Direct execution based on agent_type
            if blueprint.agent_type == "single":
                result = await self._execute_single(
                    venture_id=venture_id,
                    execution_id=execution_id,
                    blueprint=blueprint,
                    task=request.task,
                    context=request.context,
                    trace_id=trace_id,
                    start_time=start_time,
                )
            elif blueprint.agent_type in ("chain", "parallel", "router"):
                # For multi-agent types, start a Temporal workflow
                result = await self._execute_via_workflow(
                    venture_id=venture_id,
                    execution_id=execution_id,
                    blueprint=blueprint,
                    request=request,
                    trace_id=trace_id,
                    start_time=start_time,
                )
            else:
                raise ValueError(f"Unknown agent_type: {blueprint.agent_type}")

            await self._event_bus.publish(
                event_type="agent.execution.completed",
                source_module="agent_factory",
                payload={
                    "execution_id": execution_id,
                    "agent_id": blueprint.id,
                    "status": result.status,
                    "cost_usd": result.cost_usd,
                    "duration_ms": result.duration_ms,
                },
                venture_id=venture_id,
                correlation_id=execution_id,
            )
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            await self._event_bus.publish(
                event_type="agent.execution.failed",
                source_module="agent_factory",
                payload={
                    "execution_id": execution_id,
                    "agent_id": blueprint.id,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                venture_id=venture_id,
                correlation_id=execution_id,
            )
            logger.error(
                "agent_execution_failed",
                execution_id=execution_id,
                agent_id=blueprint.id,
                error=str(e),
                venture_id=venture_id,
            )
            raise

    async def _execute_single(
        self,
        venture_id: str,
        execution_id: str,
        blueprint: AgentBlueprintResponse,
        task: str,
        context: dict[str, Any],
        trace_id: str,
        start_time: float,
    ) -> AgentExecutionResult:
        """Execute a single agent — one LLM call with system prompt + task."""
        messages: list[dict[str, str]] = []

        # Build system message
        if blueprint.system_prompt:
            messages.append({"role": "system", "content": blueprint.system_prompt})

        # Build user message with task and context
        user_content = task
        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            user_content = f"{task}\n\nContext:\n{context_str}"
        messages.append({"role": "user", "content": user_content})

        async with self._tracer.span(
            "agent_factory",
            "execute_single",
            input_data={"agent_id": blueprint.id, "task": task[:200]},
        ) as span:
            response = await generate(
                messages=messages,
                model=blueprint.model,
                temperature=blueprint.temperature,
                max_tokens=blueprint.max_tokens,
                venture_id=venture_id,
                module_name="agent_factory",
                idempotency_key=execution_id,
            )

            span.set_cost(
                cost_usd=response.cost_usd,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                model=response.model,
            )

        duration_ms = (time.time() - start_time) * 1000

        return AgentExecutionResult(
            execution_id=execution_id,
            agent_id=blueprint.id,
            status="completed",
            output=response.content,
            cost_usd=response.cost_usd,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            duration_ms=duration_ms,
            trace_id=trace_id,
        )

    async def _execute_with_approval(
        self,
        venture_id: str,
        execution_id: str,
        blueprint: AgentBlueprintResponse,
        request: AgentExecutionRequest,
        trace_id: str,
        start_time: float,
    ) -> AgentExecutionResult:
        """Start an approval workflow — executes agent then pauses for human review."""
        from ai_flywheel.core.tasks import start_workflow

        from .execution import ApprovalAgentWorkflow, ApprovalWorkflowInput

        workflow_input = ApprovalWorkflowInput(
            agent_config=blueprint.model_dump(mode="json"),
            task=request.task,
            context=request.context,
            venture_id=venture_id,
            execution_id=execution_id,
        )

        await start_workflow(
            ApprovalAgentWorkflow,
            workflow_input,
            workflow_id=f"agent-approval-{execution_id}",
        )

        await self._event_bus.publish(
            event_type="agent.approval.requested",
            source_module="agent_factory",
            payload={
                "execution_id": execution_id,
                "agent_id": blueprint.id,
                "agent_name": blueprint.name,
                "task": request.task[:200],
                "workflow_id": f"agent-approval-{execution_id}",
            },
            venture_id=venture_id,
            correlation_id=execution_id,
        )

        duration_ms = (time.time() - start_time) * 1000

        return AgentExecutionResult(
            execution_id=execution_id,
            agent_id=blueprint.id,
            status="pending_approval",
            output=None,
            cost_usd=0.0,
            tokens_input=0,
            tokens_output=0,
            duration_ms=duration_ms,
            trace_id=trace_id,
        )

    async def _execute_via_workflow(
        self,
        venture_id: str,
        execution_id: str,
        blueprint: AgentBlueprintResponse,
        request: AgentExecutionRequest,
        trace_id: str,
        start_time: float,
    ) -> AgentExecutionResult:
        """Execute a multi-agent workflow (chain, parallel, router) via Temporal."""
        from ai_flywheel.core.tasks import get_workflow_result, start_workflow

        from .execution import (
            ChainAgentWorkflow,
            ChainWorkflowInput,
            ParallelAgentWorkflow,
            ParallelWorkflowInput,
        )

        workflow_id = f"agent-{blueprint.agent_type}-{execution_id}"

        if blueprint.agent_type == "chain":
            workflow_input = ChainWorkflowInput(
                agent_config=blueprint.model_dump(mode="json"),
                task=request.task,
                context=request.context,
                venture_id=venture_id,
                execution_id=execution_id,
            )
            await start_workflow(
                ChainAgentWorkflow,
                workflow_input,
                workflow_id=workflow_id,
            )
        elif blueprint.agent_type in ("parallel", "router"):
            workflow_input_parallel = ParallelWorkflowInput(
                agent_config=blueprint.model_dump(mode="json"),
                task=request.task,
                context=request.context,
                venture_id=venture_id,
                execution_id=execution_id,
            )
            await start_workflow(
                ParallelAgentWorkflow,
                workflow_input_parallel,
                workflow_id=workflow_id,
            )

        # Wait for workflow result
        result_data = await get_workflow_result(workflow_id)

        duration_ms = (time.time() - start_time) * 1000

        return AgentExecutionResult(
            execution_id=execution_id,
            agent_id=blueprint.id,
            status=result_data.get("status", "completed"),
            output=result_data.get("output"),
            cost_usd=result_data.get("cost_usd", 0.0),
            tokens_input=result_data.get("tokens_input", 0),
            tokens_output=result_data.get("tokens_output", 0),
            duration_ms=duration_ms,
            trace_id=trace_id,
        )
