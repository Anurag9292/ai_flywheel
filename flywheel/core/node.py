"""The Layer 1 node abstraction and the Runtime that wires nodes to the bus.

A **node** is an event-triggered handler: it *reacts to* one or more event
types, does work (optionally calling library tools / the LLM gateway), and
*emits* result events. Nodes are decoupled — they never call each other
directly; they only speak events (``new_docs/README.md`` §"Layer 1").

The **Runtime** is the small amount of glue that:

  1. subscribes each node to the bus for the event types it reacts to, and
  2. routes every invocation through the ``TraceRecorder`` so observability is
     automatic — the node author never wires tracing themselves.

A node never imports the bus or the recorder. It receives a ``NodeContext``
whose only capability (for now) is ``emit``. This keeps nodes pure and testable
and keeps the substrate swappable underneath them.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from flywheel.core.events import Event, EventBus, Handler
from flywheel.core.substrate import TraceRecorder


class NodeContext:
    """What a node is allowed to do with the outside world.

    Deliberately tiny: a node collects the events it wants to emit via
    ``emit(...)``. The Runtime publishes them *after* the trace is recorded, so
    a node's emissions and its trace stay consistent. (Future: the context will
    also expose ``get_agent(...)`` and library-tool handles — see
    ``new_docs/stack.md`` "Agent seam".)
    """

    def __init__(self, triggering_event: Event) -> None:
        self.triggering_event = triggering_event
        self._emitted: list[Event] = []

    def emit(self, type: str, payload: dict[str, Any] | None = None, **kw: Any) -> Event:
        """Queue a follow-on event that inherits venture + correlation id."""
        event = self.triggering_event.child(type=type, payload=payload or {}, **kw)
        self._emitted.append(event)
        return event

    @property
    def emitted(self) -> list[Event]:
        return list(self._emitted)


@runtime_checkable
class Node(Protocol):
    """The contract every Layer 1 node satisfies.

    - ``name`` / ``version`` identify the node in traces (the version is what
      lets us tell ``post-drafter`` impl ``human`` from ``agent-v1`` apart —
      see the implementation-swap convention in ``layer1-nodes.md``).
    - ``reacts_to`` is the list of event types that trigger this node.
    - ``handle`` does the work, emitting via the context.
    """

    name: str
    version: str
    reacts_to: list[str]

    def handle(self, event: Event, ctx: NodeContext) -> None: ...


class Runtime:
    """Registers nodes on the bus and dispatches events through the recorder."""

    def __init__(self, bus: EventBus, recorder: TraceRecorder) -> None:
        self._bus = bus
        self._recorder = recorder
        self._nodes: list[Node] = []

    def register(self, node: Node) -> None:
        """Subscribe ``node`` to each event type it reacts to.

        Every subscription is wrapped so that, when the event fires, the node's
        ``handle`` runs *inside* the trace-recorder and any emitted events are
        published afterwards.
        """
        self._nodes.append(node)
        for event_type in node.reacts_to:
            self._bus.subscribe(event_type, self._make_handler(node))

    def _make_handler(self, node: Node) -> Handler:
        def handler(event: Event) -> None:
            ctx = NodeContext(triggering_event=event)

            def run() -> list[Event]:
                node.handle(event, ctx)
                return ctx.emitted

            emitted = self._recorder.record(
                node_name=node.name,
                node_version=node.version,
                triggering_event=event,
                handle=run,
            )
            # Publish the node's outputs only after the trace is captured.
            for out in emitted:
                self._bus.publish(out)

        return handler

    @property
    def nodes(self) -> list[Node]:
        return list(self._nodes)
