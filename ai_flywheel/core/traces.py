"""Trace & Observability — distributed tracing for all platform operations.

Every module operation is traced with timing, cost, and I/O data.
Traces are written asynchronously to avoid blocking operations.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, ParamSpec, TypeVar

import structlog
import uuid7 as uuid7_lib

logger = structlog.get_logger()

# Context variables for trace propagation
_current_trace_id: ContextVar[str | None] = ContextVar("current_trace_id", default=None)
_current_span_id: ContextVar[str | None] = ContextVar("current_span_id", default=None)
_current_venture_id: ContextVar[str | None] = ContextVar("current_venture_id", default=None)

P = ParamSpec("P")
R = TypeVar("R")


def _generate_id() -> str:
    return str(uuid7_lib.uuid7())


class SpanData:
    """Holds data for a single trace span."""

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: str | None,
        venture_id: str | None,
        module_name: str,
        operation: str,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.venture_id = venture_id
        self.module_name = module_name
        self.operation = operation
        self.started_at = datetime.now(UTC)
        self.ended_at: datetime | None = None
        self.duration_ms: float | None = None
        self.status: str = "ok"
        self.cost_usd: float = 0.0
        self.tokens_input: int = 0
        self.tokens_output: int = 0
        self.model_name: str | None = None
        self.input_data: dict[str, Any] | None = None
        self.output_data: dict[str, Any] | None = None
        self.error_message: str | None = None
        self.metadata: dict[str, Any] = {}

    def set_cost(
        self,
        cost_usd: float,
        tokens_input: int = 0,
        tokens_output: int = 0,
        model: str | None = None,
    ) -> None:
        """Record LLM cost on this span."""
        self.cost_usd = cost_usd
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.model_name = model

    def set_error(self, error: Exception) -> None:
        """Mark span as errored."""
        self.status = "error"
        self.error_message = f"{type(error).__name__}: {error}"

    def finish(self) -> None:
        """Mark span as complete."""
        self.ended_at = datetime.now(UTC)
        self.duration_ms = (self.ended_at - self.started_at).total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """Serialize for persistence."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "venture_id": self.venture_id,
            "module_name": self.module_name,
            "operation": self.operation,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "cost_usd": self.cost_usd,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "model_name": self.model_name,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class Tracer:
    """Manages span creation and persistence."""

    def __init__(self) -> None:
        self._pending_spans: list[SpanData] = []

    def set_venture_context(self, venture_id: str) -> None:
        """Set the current venture for trace attribution."""
        _current_venture_id.set(venture_id)

    @asynccontextmanager
    async def span(
        self,
        module_name: str,
        operation: str,
        input_data: dict[str, Any] | None = None,
    ):
        """Create a trace span as a context manager.

        Usage:
            async with tracer.span("llm_gateway", "complete") as span:
                result = await llm.complete(...)
                span.set_cost(0.03, tokens_input=150, tokens_output=50)
        """
        trace_id = _current_trace_id.get() or _generate_id()
        parent_span_id = _current_span_id.get()
        span_id = _generate_id()
        venture_id = _current_venture_id.get()

        trace_token = _current_trace_id.set(trace_id)
        span_token = _current_span_id.set(span_id)

        span_data = SpanData(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            venture_id=venture_id,
            module_name=module_name,
            operation=operation,
        )
        span_data.input_data = input_data

        try:
            yield span_data
        except Exception as e:
            span_data.set_error(e)
            raise
        finally:
            span_data.finish()
            self._pending_spans.append(span_data)
            _current_trace_id.reset(trace_token)
            _current_span_id.reset(span_token)

            logger.debug(
                "span_completed",
                trace_id=trace_id,
                module=module_name,
                operation=operation,
                duration_ms=span_data.duration_ms,
                cost_usd=span_data.cost_usd,
                status=span_data.status,
            )

    def start_trace(self, venture_id: str | None = None) -> str:
        """Start a new trace. Returns the trace_id."""
        trace_id = _generate_id()
        _current_trace_id.set(trace_id)
        _current_span_id.set(None)
        if venture_id:
            _current_venture_id.set(venture_id)
        return trace_id

    def get_pending_spans(self) -> list[SpanData]:
        """Get and clear pending spans for persistence."""
        spans = self._pending_spans.copy()
        self._pending_spans.clear()
        return spans


def traced(
    module_name: str = "unknown",
    operation: str | None = None,
) -> Callable:
    """Decorator to automatically trace an async function."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            op_name = operation or func.__name__
            tracer = get_tracer()
            async with tracer.span(module_name, op_name):
                return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


# Global tracer instance
_global_tracer = Tracer()


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    return _global_tracer
