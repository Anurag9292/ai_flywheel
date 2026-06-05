"""Event listener for Cost Optimizer — captures cost data from platform events.

Subscribes to relevant events (LLM calls, agent executions, etc.) and
routes cost information to the CostOptimizer service for tracking and
budget enforcement.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from ai_flywheel.core.events import Event, EventBus

from .service import CostOptimizer

logger = structlog.get_logger()

# Events that typically carry cost data
_COST_BEARING_EVENT_PREFIXES = (
    "agent.execution.completed",
    "llm.",
    "cost.",
)

# Fields to look for in event payloads that indicate cost
_COST_PAYLOAD_FIELDS = ("cost_usd", "amount_usd")


async def _handle_cost_event(event: Event) -> None:
    """Handle events that may contain cost data.

    Extracts cost information from the event payload and records it
    via the CostOptimizer service. Skips events that don't contain
    actionable cost data or that originated from cost_optimizer itself
    (to avoid feedback loops).
    """
    # Skip events from ourselves to avoid loops
    if event.source_module == "cost_optimizer":
        return

    # Skip events without a venture context
    if not event.venture_id:
        return

    payload = event.payload
    if not payload:
        return

    # Extract cost from payload
    amount_usd: float | None = None
    for field in _COST_PAYLOAD_FIELDS:
        if field in payload and payload[field]:
            try:
                amount_usd = float(payload[field])
            except (ValueError, TypeError):
                continue
            if amount_usd > 0:
                break

    if not amount_usd or amount_usd <= 0:
        return

    # Extract other metadata
    module_name = payload.get("module_name") or event.source_module
    operation = payload.get("operation") or event.event_type
    provider = payload.get("provider", "unknown")
    model_name = payload.get("model_name") or payload.get("model")
    tokens_input = int(payload.get("tokens_input", 0))
    tokens_output = int(payload.get("tokens_output", 0))

    # Build metadata from remaining payload fields
    metadata_keys = {
        "execution_id",
        "agent_id",
        "trace_id",
        "correlation_id",
    }
    metadata = {k: v for k, v in payload.items() if k in metadata_keys and v}

    try:
        optimizer = CostOptimizer()
        await optimizer.record_cost(
            venture_id=event.venture_id,
            module_name=module_name,
            operation=operation,
            amount_usd=amount_usd,
            provider=provider,
            model_name=model_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            metadata=metadata or None,
        )
    except Exception as e:
        logger.error(
            "cost_listener_record_failed",
            event_type=event.event_type,
            venture_id=event.venture_id,
            error=str(e),
        )


async def _periodic_budget_check(
    optimizer: CostOptimizer,
    venture_ids_provider: Any = None,
    interval_seconds: int = 300,
) -> None:
    """Periodically check budgets for all active ventures.

    Runs every `interval_seconds` (default 5 minutes) and checks
    budget status across ventures. This catches cases where spend
    accumulated from multiple small operations.

    Args:
        optimizer: CostOptimizer instance.
        venture_ids_provider: Callable that returns active venture IDs.
            If None, budget checks rely on event-driven triggers only.
        interval_seconds: How often to run checks.
    """
    while True:
        try:
            await asyncio.sleep(interval_seconds)

            if venture_ids_provider:
                venture_ids = await venture_ids_provider()
                for venture_id in venture_ids:
                    try:
                        await optimizer.check_budget(venture_id)
                    except Exception as e:
                        logger.error(
                            "periodic_budget_check_failed",
                            venture_id=venture_id,
                            error=str(e),
                        )
            else:
                logger.debug("periodic_budget_check_skipped_no_provider")

        except asyncio.CancelledError:
            logger.info("periodic_budget_check_stopped")
            break
        except Exception as e:
            logger.error("periodic_budget_check_error", error=str(e))


def setup_cost_listener(
    event_bus: EventBus,
    venture_ids_provider: Any = None,
    periodic_interval: int = 300,
) -> None:
    """Register the cost event handler on the event bus.

    Subscribes to all events ('*') and filters for cost-bearing ones.
    Also starts a background task for periodic budget checks.

    Args:
        event_bus: The EventBus instance to subscribe to.
        venture_ids_provider: Optional async callable returning venture IDs
            for periodic budget checks.
        periodic_interval: Seconds between periodic budget checks.
    """
    # Subscribe to all events — the handler filters internally
    event_bus.subscribe("*", _handle_cost_event)

    # Start periodic budget check as a background task
    optimizer = CostOptimizer()
    asyncio.create_task(
        _periodic_budget_check(
            optimizer=optimizer,
            venture_ids_provider=venture_ids_provider,
            interval_seconds=periodic_interval,
        )
    )

    logger.info(
        "cost_listener_setup",
        subscription="*",
        periodic_interval=periodic_interval,
    )
