"""The event contract and the event bus.

``Event`` is the universal envelope that flows between Layer 1 nodes. Every
node *reacts to* events and *emits* events; the bus is the only dependency that
every other capability shares (see ``new_docs/layer1-nodes.md`` §1 Substrate).

The bus is defined as a ``Protocol`` (``EventBus``) with a thin first
implementation (``InMemoryEventBus``). This is the "fake/real seam" from
``new_docs/stack.md``: program against the interface now, swap in Redis Streams
or Kafka later — without touching a single node.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid.uuid4().hex


class Event(BaseModel):
    """The universal event envelope.

    Naming convention (``new_docs/layer1-nodes.md``): ``<domain>.<verb>`` —
    past tense for things that happened (``campaign.launched``), present tense
    + ``.requested`` for things being asked for (``research.requested``).

    Required envelope fields per the conventions section of that doc:
    ``venture_id``, ``correlation_id``, ``emitted_at``. ``correlation_id`` is
    what lets Layer 3 trace a whole chain of reactions back to the originating
    event — a child event copies its parent's ``correlation_id``.
    """

    type: str = Field(description="Event type as <domain>.<verb>.")
    venture_id: str = Field(description="The venture this event belongs to.")
    payload: dict[str, Any] = Field(default_factory=dict)

    # Envelope / tracing metadata.
    event_id: str = Field(default_factory=_new_id)
    correlation_id: str = Field(default_factory=_new_id)
    emitted_at: datetime = Field(default_factory=_utcnow)

    # Meta-tags (not event types). e.g. ``requires_human`` / ``urgent``.
    tags: dict[str, Any] = Field(default_factory=dict)

    def child(self, type: str, payload: dict[str, Any] | None = None, **kw: Any) -> Event:
        """Create a follow-on event that inherits this event's venture and
        correlation id, so the causal chain stays linked for Layer 3.
        """
        return Event(
            type=type,
            venture_id=self.venture_id,
            correlation_id=self.correlation_id,
            payload=payload or {},
            **kw,
        )


# A handler is any callable that takes an Event and returns nothing. Nodes are
# wrapped into handlers by the Runtime; you rarely register raw handlers.
Handler = Callable[[Event], None]


@runtime_checkable
class EventBus(Protocol):
    """The pub/sub contract. Thin now (in-memory, synchronous); the same
    interface fronts Redis Streams / Kafka later.
    """

    def subscribe(self, event_type: str, handler: Handler) -> None: ...

    def publish(self, event: Event) -> None: ...


class InMemoryEventBus:
    """Synchronous, in-process pub/sub — the walking-skeleton implementation.

    Deferred per ``new_docs/stack.md`` until "multiple processes/workers, or
    events must survive a restart": Redis Streams → Kafka. Until then, a dict of
    subscriber lists dispatched synchronously is all we need to prove the
    event-driven model.

    Supports a wildcard subscription on ``"*"`` — used by the trace-recorder /
    Layer 3 to observe *every* event.
    """

    WILDCARD = "*"

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        # Exact-type subscribers, then wildcard observers.
        for handler in list(self._subscribers.get(event.type, ())):
            handler(event)
        for handler in list(self._subscribers.get(self.WILDCARD, ())):
            handler(event)
