"""Event Bus — pub/sub for inter-module communication.

Phase 0: In-process with async handlers.
Production: Redis Streams for distributed pub/sub.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

import structlog
import uuid

logger = structlog.get_logger()

EventHandler = Callable[["Event"], Coroutine[Any, Any, None]]


class Event:
    """A platform event with type, source, and payload."""

    def __init__(
        self,
        event_type: str,
        source_module: str,
        payload: dict[str, Any],
        venture_id: str | None = None,
        correlation_id: str | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.source_module = source_module
        self.payload = payload
        self.venture_id = venture_id
        self.correlation_id = correlation_id or self.id
        self.timestamp = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "source_module": self.source_module,
            "payload": self.payload,
            "venture_id": self.venture_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus:
    """In-process event bus with async handlers and wildcard subscriptions."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = 1000

    async def publish(
        self,
        event_type: str,
        source_module: str,
        payload: dict[str, Any],
        venture_id: str | None = None,
        correlation_id: str | None = None,
    ) -> Event:
        """Publish an event. Matching subscribers notified asynchronously."""
        event = Event(
            event_type=event_type,
            source_module=source_module,
            payload=payload,
            venture_id=venture_id,
            correlation_id=correlation_id,
        )

        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        handlers = self._match_handlers(event_type)
        if handlers:
            tasks = [asyncio.create_task(self._safe_call(h, event)) for h in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.debug(
            "event_published",
            event_type=event_type,
            source=source_module,
            venture_id=venture_id,
            handlers=len(handlers),
        )
        return event

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type. Supports wildcards: 'agent.*' or '*'."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    def _match_handlers(self, event_type: str) -> list[EventHandler]:
        """Find handlers matching event type including wildcards."""
        handlers: list[EventHandler] = []
        handlers.extend(self._handlers.get(event_type, []))

        # Wildcard: "agent.*" matches "agent.completed"
        parts = event_type.split(".")
        for i in range(len(parts)):
            wildcard = ".".join(parts[:i]) + ".*" if i > 0 else "*"
            handlers.extend(self._handlers.get(wildcard, []))

        # Global wildcard
        if "*" not in event_type:
            handlers.extend(self._handlers.get("*", []))

        return handlers

    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        """Call handler safely, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                "event_handler_error",
                handler=handler.__name__,
                event_type=event.event_type,
                error=str(e),
            )

    def get_history(
        self,
        event_type: str | None = None,
        venture_id: str | None = None,
        limit: int = 50,
    ) -> list[Event]:
        """Get recent events from history."""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if venture_id:
            events = [e for e in events if e.venture_id == venture_id]
        return events[-limit:]


# Global instance
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return _event_bus
