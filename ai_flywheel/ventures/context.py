"""Venture context — binds a venture_id for the duration of a request/workflow.

Uses contextvars for safe async propagation and integrates with the tracer
to ensure all spans are attributed to the correct venture.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar

import structlog

from ai_flywheel.core.traces import get_tracer

logger = structlog.get_logger()

# Context variable holding the active venture_id
_venture_id_var: ContextVar[str | None] = ContextVar(
    "venture_id", default=None
)


def get_current_venture_id() -> str | None:
    """Return the current venture_id, or None if not set."""
    return _venture_id_var.get()


def require_venture_id() -> str:
    """Return the current venture_id or raise if not set.

    Raises:
        RuntimeError: If no venture context is active.
    """
    venture_id = _venture_id_var.get()
    if venture_id is None:
        raise RuntimeError(
            "No venture context is active. "
            "Wrap the operation in `venture_context(venture_id)` or "
            "ensure the request middleware has set the venture scope."
        )
    return venture_id


@asynccontextmanager
async def venture_context(venture_id: str) -> AsyncGenerator[str, None]:
    """Bind a venture_id for the lifetime of an async block.

    Sets the venture on:
    - The local contextvar (for get_current_venture_id / require_venture_id)
    - The tracer (so all spans created within are attributed)

    Usage:
        async with venture_context("ven_abc123") as vid:
            # All operations here are scoped to ven_abc123
            ...
    """
    token = _venture_id_var.set(venture_id)
    tracer = get_tracer()
    tracer.set_venture_context(venture_id)

    logger.debug("venture_context_entered", venture_id=venture_id)
    try:
        yield venture_id
    finally:
        _venture_id_var.reset(token)
        logger.debug("venture_context_exited", venture_id=venture_id)
