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

    Introspection metadata (used by ``Runtime.describe()`` for the topology
    visualization — see ``new_docs/visualization.md``). These are declarative
    labels only; they do not affect dispatch:

    - ``kind`` — ``"dumb"`` or ``"agentic"``.
    - ``emits`` — event types the node emits.
    - ``calls`` — library tools / gateways the node calls.

    They are optional on a node object; ``describe()`` reads them defensively.
    """

    name: str
    version: str
    reacts_to: list[str]
    kind: str
    emits: list[str]
    calls: list[str]

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

    def describe(self) -> dict[str, Any]:
        """Return a code-derived topology graph of the registered nodes.

        This is the single source of truth for the visualization
        (``new_docs/visualization.md``). It walks every registered node and its
        declared metadata and produces:

        - ``nodes``    — name, version, kind, reacts_to, emits, calls
        - ``libraries``— the set of library tools referenced via ``calls``
        - ``events``   — every event type seen, with who emits / reacts to it
        - ``edges``    — ``reacts`` (event→node), ``emits`` (node→event),
                          ``calls`` (node→library)
        - ``substrate``— the always-on trace-recorder that wraps every node
        - ``lint``     — orphan events (emitted but nothing reacts; reacted-to
                          but nothing emits) — a cheap correctness check

        It is pure (no side effects) and safe to call at any time.
        """
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        libraries: set[str] = set()
        emitters: dict[str, list[str]] = {}
        reactors: dict[str, list[str]] = {}

        for node in self._nodes:
            reacts_to = list(getattr(node, "reacts_to", []))
            emits = list(getattr(node, "emits", []))
            calls = list(getattr(node, "calls", []))
            nodes.append(
                {
                    "name": node.name,
                    "version": node.version,
                    "kind": getattr(node, "kind", "dumb"),
                    "reacts_to": reacts_to,
                    "emits": emits,
                    "calls": calls,
                }
            )
            for event_type in reacts_to:
                reactors.setdefault(event_type, []).append(node.name)
                edges.append(
                    {"source": event_type, "target": node.name, "kind": "reacts"}
                )
            for event_type in emits:
                emitters.setdefault(event_type, []).append(node.name)
                edges.append(
                    {"source": node.name, "target": event_type, "kind": "emits"}
                )
            for lib in calls:
                libraries.add(lib)
                edges.append({"source": node.name, "target": lib, "kind": "calls"})

        all_event_types = sorted(set(emitters) | set(reactors))
        events = [
            {
                "type": t,
                "emitted_by": sorted(emitters.get(t, [])),
                "reacted_by": sorted(reactors.get(t, [])),
            }
            for t in all_event_types
        ]

        lint = {
            # Emitted by some node but nothing subscribes (a dead end).
            "orphan_emitted": [
                t for t in all_event_types if emitters.get(t) and not reactors.get(t)
            ],
            # Reacted to but no registered node emits it (relies on external/seed events).
            "unproduced_reacted": [
                t for t in all_event_types if reactors.get(t) and not emitters.get(t)
            ],
        }

        return {
            "nodes": nodes,
            "libraries": sorted(libraries),
            "events": events,
            "edges": edges,
            "substrate": {"name": "trace-recorder", "wraps": [n["name"] for n in nodes]},
            "lint": lint,
        }
