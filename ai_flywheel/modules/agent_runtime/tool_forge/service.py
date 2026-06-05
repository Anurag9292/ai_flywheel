"""Tool Forge — registry, invocation, and observability for agent tools.

The ToolForge service manages the lifecycle of tools that agents can invoke:
- Registration and CRUD for tool definitions
- HTTP-based tool invocation with timeout handling
- Execution recording and reliability tracking
- Keyword search over available tools

Usage:
    forge = ToolForge()
    tool = await forge.register_tool(venture_id, ToolCreate(
        name="stripe-charge",
        description="Create a Stripe charge",
        category="payment",
        config={"base_url": "https://api.stripe.com", "method": "POST", "path": "/v1/charges", ...},
    ))
    result = await forge.invoke(venture_id, ToolInvokeRequest(
        tool_name="stripe-charge",
        parameters={"amount": 2000, "currency": "usd"},
    ))
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from sqlalchemy import or_, select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .models import ToolDefinition, ToolExecution
from .schemas import (
    ToolCreate,
    ToolInvokeRequest,
    ToolInvokeResult,
    ToolResponse,
    ToolSearchRequest,
    ToolSearchResult,
    ToolUpdate,
)

logger = structlog.get_logger()


class ToolForge:
    """Registry and execution engine for agent tools.

    Manages tool definitions, handles HTTP-based invocation with timeout
    and retry semantics, tracks reliability metrics, and emits events for
    observability.
    """

    def __init__(self) -> None:
        self._event_bus = get_event_bus()
        self._tracer = get_tracer()

    async def register_tool(
        self, venture_id: str, data: ToolCreate
    ) -> ToolResponse:
        """Register a new tool definition for a venture."""
        async with get_session(venture_id) as session:
            tool = ToolDefinition(
                venture_id=venture_id,
                name=data.name,
                description=data.description,
                category=data.category,
                input_schema=data.input_schema,
                output_schema=data.output_schema,
                config=data.config,
            )
            session.add(tool)
            await session.flush()

            response = ToolResponse.model_validate(tool)

        await self._event_bus.publish(
            event_type="tool.registered",
            source_module="tool_forge",
            payload={
                "tool_id": response.id,
                "name": response.name,
                "category": response.category,
            },
            venture_id=venture_id,
        )

        logger.info(
            "tool_registered",
            tool_id=response.id,
            name=response.name,
            category=response.category,
            venture_id=venture_id,
        )
        return response

    async def get_tool(self, venture_id: str, tool_id: str) -> ToolResponse:
        """Get a tool definition by ID."""
        async with get_session(venture_id) as session:
            stmt = select(ToolDefinition).where(
                ToolDefinition.id == tool_id,
                ToolDefinition.venture_id == venture_id,
                ToolDefinition.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            tool = result.scalar_one()
            return ToolResponse.model_validate(tool)

    async def get_tool_by_name(self, venture_id: str, name: str) -> ToolResponse:
        """Get a tool definition by name within a venture."""
        async with get_session(venture_id) as session:
            stmt = select(ToolDefinition).where(
                ToolDefinition.name == name,
                ToolDefinition.venture_id == venture_id,
                ToolDefinition.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            tool = result.scalar_one()
            return ToolResponse.model_validate(tool)

    async def list_tools(
        self, venture_id: str, category: str | None = None
    ) -> list[ToolResponse]:
        """List all active tool definitions for a venture, optionally filtered by category."""
        async with get_session(venture_id) as session:
            stmt = select(ToolDefinition).where(
                ToolDefinition.venture_id == venture_id,
                ToolDefinition.deleted_at.is_(None),
                ToolDefinition.is_active.is_(True),
            )
            if category:
                stmt = stmt.where(ToolDefinition.category == category)
            stmt = stmt.order_by(ToolDefinition.created_at.desc())

            result = await session.execute(stmt)
            tools = result.scalars().all()
            return [ToolResponse.model_validate(t) for t in tools]

    async def update_tool(
        self, venture_id: str, tool_id: str, data: ToolUpdate
    ) -> ToolResponse:
        """Update a tool definition. Increments version on changes."""
        async with get_session(venture_id) as session:
            stmt = select(ToolDefinition).where(
                ToolDefinition.id == tool_id,
                ToolDefinition.venture_id == venture_id,
                ToolDefinition.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            tool = result.scalar_one()

            update_data = data.model_dump(exclude_unset=True)
            if update_data:
                for field, value in update_data.items():
                    setattr(tool, field, value)
                tool.version += 1

            await session.flush()
            response = ToolResponse.model_validate(tool)

        await self._event_bus.publish(
            event_type="tool.updated",
            source_module="tool_forge",
            payload={
                "tool_id": response.id,
                "name": response.name,
                "version": response.version,
            },
            venture_id=venture_id,
        )

        logger.info(
            "tool_updated",
            tool_id=response.id,
            name=response.name,
            version=response.version,
            venture_id=venture_id,
        )
        return response

    async def invoke(
        self, venture_id: str, request: ToolInvokeRequest
    ) -> ToolInvokeResult:
        """Invoke a tool — the core execution method.

        Resolves the tool definition, validates input parameters, makes the HTTP
        request, records the execution, and updates reliability stats.
        """
        self._tracer.set_venture_context(venture_id)
        start_time = time.time()

        # Resolve tool definition
        if request.tool_id:
            tool_response = await self.get_tool(venture_id, request.tool_id)
        elif request.tool_name:
            tool_response = await self.get_tool_by_name(venture_id, request.tool_name)
        else:
            raise ValueError("Either tool_id or tool_name must be provided")

        tool_id = tool_response.id

        # Validate input parameters against input_schema (basic type checking)
        self._validate_parameters(request.parameters, tool_response.input_schema or {})

        async with self._tracer.span(
            "tool_forge",
            "invoke",
            input_data={
                "tool_id": tool_id,
                "tool_name": tool_response.name,
                "parameters": request.parameters,
            },
        ) as span:
            status = "success"
            output_data: dict[str, Any] | None = None
            error_message: str | None = None

            try:
                output_data = await self._execute_http_request(
                    config=tool_response.config or {},
                    parameters=request.parameters,
                    timeout_ms=request.timeout_ms,
                )
            except httpx.TimeoutException:
                status = "timeout"
                error_message = (
                    f"Tool invocation timed out after {request.timeout_ms}ms"
                )
                span.set_error(
                    TimeoutError(error_message)
                )
            except Exception as e:
                status = "failure"
                error_message = f"{type(e).__name__}: {e}"
                span.set_error(e)

            duration_ms = (time.time() - start_time) * 1000
            span.metadata["duration_ms"] = duration_ms
            span.metadata["status"] = status

        # Record execution
        execution_id = await self._record_execution(
            venture_id=venture_id,
            tool_id=tool_id,
            agent_id=request.agent_id,
            status=status,
            input_data=request.parameters,
            output_data=output_data,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        # Update tool stats
        await self._update_tool_stats(
            venture_id=venture_id,
            tool_id=tool_id,
            status=status,
            duration_ms=duration_ms,
        )

        # Emit events
        if status == "success":
            await self._event_bus.publish(
                event_type="tool.invoked",
                source_module="tool_forge",
                payload={
                    "execution_id": execution_id,
                    "tool_id": tool_id,
                    "tool_name": tool_response.name,
                    "agent_id": request.agent_id,
                    "duration_ms": duration_ms,
                    "status": status,
                },
                venture_id=venture_id,
            )
        else:
            await self._event_bus.publish(
                event_type="tool.failed",
                source_module="tool_forge",
                payload={
                    "execution_id": execution_id,
                    "tool_id": tool_id,
                    "tool_name": tool_response.name,
                    "agent_id": request.agent_id,
                    "status": status,
                    "error": error_message,
                    "duration_ms": duration_ms,
                },
                venture_id=venture_id,
            )

        logger.info(
            "tool_invoked",
            tool_id=tool_id,
            tool_name=tool_response.name,
            status=status,
            duration_ms=round(duration_ms, 2),
            venture_id=venture_id,
        )

        return ToolInvokeResult(
            execution_id=execution_id,
            tool_id=tool_id,
            status=status,
            output=output_data,
            error=error_message,
            duration_ms=duration_ms,
            cost_usd=0.0,
        )

    async def search(
        self, venture_id: str, request: ToolSearchRequest
    ) -> ToolSearchResult:
        """Search tools by keyword over name and description."""
        async with get_session(venture_id) as session:
            # Keyword search using ILIKE for simplicity
            pattern = f"%{request.query}%"
            stmt = select(ToolDefinition).where(
                ToolDefinition.venture_id == venture_id,
                ToolDefinition.deleted_at.is_(None),
                ToolDefinition.is_active.is_(True),
                or_(
                    ToolDefinition.name.ilike(pattern),
                    ToolDefinition.description.ilike(pattern),
                ),
            )
            if request.category:
                stmt = stmt.where(ToolDefinition.category == request.category)
            stmt = stmt.order_by(ToolDefinition.reliability_score.desc())
            stmt = stmt.limit(request.limit)

            result = await session.execute(stmt)
            tools = result.scalars().all()

        return ToolSearchResult(
            tools=[ToolResponse.model_validate(t) for t in tools],
            query=request.query,
        )

    async def get_execution_history(
        self, venture_id: str, tool_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get recent execution records for a tool."""
        async with get_session(venture_id) as session:
            stmt = (
                select(ToolExecution)
                .where(
                    ToolExecution.venture_id == venture_id,
                    ToolExecution.tool_id == tool_id,
                    ToolExecution.deleted_at.is_(None),
                )
                .order_by(ToolExecution.created_at.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            executions = result.scalars().all()

            return [
                {
                    "id": ex.id,
                    "tool_id": ex.tool_id,
                    "agent_id": ex.agent_id,
                    "status": ex.status,
                    "input_data": ex.input_data,
                    "output_data": ex.output_data,
                    "error_message": ex.error_message,
                    "duration_ms": ex.duration_ms,
                    "cost_usd": ex.cost_usd,
                    "created_at": ex.created_at.isoformat(),
                }
                for ex in executions
            ]

    # ─── Private helpers ──────────────────────────────────────────────────

    def _validate_parameters(
        self, parameters: dict[str, Any], input_schema: dict[str, Any]
    ) -> None:
        """Basic type validation of input parameters against the tool's input_schema.

        The input_schema is expected as a dict of parameter_name -> type_string mappings.
        Example: {"amount": "integer", "currency": "string"}
        """
        if not input_schema:
            return

        type_map: dict[str, type | tuple[type, ...]] = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        for param_name, expected_type in input_schema.items():
            if param_name not in parameters:
                # Missing optional params are acceptable; strict enforcement
                # can be added via a "required" field in the schema later
                continue

            if not isinstance(expected_type, str):
                continue

            python_type = type_map.get(expected_type.lower())
            if python_type and not isinstance(parameters[param_name], python_type):
                raise ValueError(
                    f"Parameter '{param_name}' expected type '{expected_type}', "
                    f"got '{type(parameters[param_name]).__name__}'"
                )

    async def _execute_http_request(
        self,
        config: dict[str, Any],
        parameters: dict[str, Any],
        timeout_ms: int,
    ) -> dict[str, Any]:
        """Make the HTTP request to the tool's endpoint."""
        url = f"{config.get('base_url', '')}{config.get('path', '')}"
        method = config.get("method", "POST").upper()
        headers = dict(config.get("headers", {}))

        # Add auth if configured
        if config.get("auth_type") == "bearer":
            headers["Authorization"] = f"Bearer {config.get('api_key', '')}"
        elif config.get("auth_type") == "basic":
            # For basic auth, api_key is expected as "username:password"
            import base64

            credentials = config.get("api_key", ":")
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        timeout_seconds = timeout_ms / 1000.0

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            if method in ("POST", "PUT", "PATCH"):
                response = await client.request(
                    method=method,
                    url=url,
                    json=parameters,
                    headers=headers,
                )
            else:
                response = await client.request(
                    method=method,
                    url=url,
                    params=parameters,
                    headers=headers,
                )

            response.raise_for_status()

            # Try to parse JSON response; fall back to text
            try:
                return response.json()
            except Exception:
                return {"raw_response": response.text}

    async def _record_execution(
        self,
        venture_id: str,
        tool_id: str,
        agent_id: str | None,
        status: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any] | None,
        error_message: str | None,
        duration_ms: float,
    ) -> str:
        """Persist a tool execution record and return its ID."""
        async with get_session(venture_id) as session:
            execution = ToolExecution(
                venture_id=venture_id,
                tool_id=tool_id,
                agent_id=agent_id,
                status=status,
                input_data=input_data,
                output_data=output_data,
                error_message=error_message,
                duration_ms=duration_ms,
                cost_usd=0.0,
            )
            session.add(execution)
            await session.flush()
            return execution.id

    async def _update_tool_stats(
        self,
        venture_id: str,
        tool_id: str,
        status: str,
        duration_ms: float,
    ) -> None:
        """Update tool reliability stats after an invocation."""
        async with get_session(venture_id) as session:
            stmt = select(ToolDefinition).where(
                ToolDefinition.id == tool_id,
                ToolDefinition.venture_id == venture_id,
            )
            result = await session.execute(stmt)
            tool = result.scalar_one()

            # Update invocation counts
            tool.total_invocations += 1
            if status in ("failure", "timeout"):
                tool.failure_count += 1

            # Update reliability score
            tool.reliability_score = 1.0 - (
                tool.failure_count / max(tool.total_invocations, 1)
            )

            # Update average latency (rolling average)
            prev_total = tool.total_invocations - 1
            if prev_total <= 0:
                tool.avg_latency_ms = duration_ms
            else:
                tool.avg_latency_ms = (
                    (tool.avg_latency_ms * prev_total) + duration_ms
                ) / tool.total_invocations

            await session.flush()
