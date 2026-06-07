"""The ``trace-recorder`` substrate.

This is the one thing in the system that is *not* "a node you call" (see
``new_docs/vision.md`` principle 6 and ``new_docs/layer1-nodes.md`` §1). It is
the always-on layer that wraps **every** node invocation, automatically
recording inputs / outputs / latency / cost — without the venture author wiring
it — and emits a ``trace.captured`` event for Layer 3 to read.

    "Without it, Layer 3 has nothing to read, and the flywheel doesn't spin."

Thin first impl (``new_docs/stack.md``): structured logging via ``structlog``
plus an append-only JSONL trace log. Target: Postgres + the wider observability
stack, swapped in behind this same call site.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from flywheel.core.events import Event, EventBus

log = structlog.get_logger("flywheel.trace")


class TraceRecorder:
    """Wraps node dispatch to capture a trace per invocation.

    Usage is *not* per-node: the Runtime hands every node's ``handle`` call
    through :meth:`record`, so observability is automatic and uniform.
    """

    def __init__(self, bus: EventBus, log_path: str | Path | None = None) -> None:
        self._bus = bus
        self._path = Path(log_path) if log_path else None
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        node_name: str,
        node_version: str,
        triggering_event: Event,
        handle: Any,
    ) -> list[Event]:
        """Run ``handle()`` for one node, timing it and capturing a trace.

        ``handle`` is a zero-arg callable that returns the list of events the
        node emitted. We time it, capture success/error, write the trace, and
        emit ``trace.captured`` — then return the emitted events to the caller
        so the Runtime can publish them.
        """
        started = time.perf_counter()
        emitted: list[Event] = []
        error: str | None = None
        try:
            emitted = list(handle() or [])
            return emitted
        except Exception as exc:  # noqa: BLE001 — substrate records, never swallows silently
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            latency_ms = (time.perf_counter() - started) * 1000.0
            self._capture(
                node_name=node_name,
                node_version=node_version,
                triggering_event=triggering_event,
                emitted=emitted,
                latency_ms=latency_ms,
                error=error,
            )

    def _capture(
        self,
        *,
        node_name: str,
        node_version: str,
        triggering_event: Event,
        emitted: list[Event],
        latency_ms: float,
        error: str | None,
    ) -> None:
        trace: dict[str, Any] = {
            "captured_at": datetime.now(UTC).isoformat(),
            "node": node_name,
            "node_version": node_version,
            "venture_id": triggering_event.venture_id,
            "correlation_id": triggering_event.correlation_id,
            "trigger_event_id": triggering_event.event_id,
            "trigger_type": triggering_event.type,
            "emitted_types": [e.type for e in emitted],
            # Event ids the node emitted — lets the timeline link this step's
            # output to the next step's trigger (parent->child causality).
            "emitted_event_ids": [e.event_id for e in emitted],
            "latency_ms": round(latency_ms, 3),
            # Cost is a placeholder until the llm-gateway lands (Step 2) and can
            # report real token cost through the context.
            "cost_usd": 0.0,
            "error": error,
        }

        log.info("trace.captured", **trace)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(trace) + "\n")

        # Emit the observable event Layer 3 subscribes to. We publish directly
        # (not via a node) because the recorder *is* substrate, beneath nodes.
        self._bus.publish(
            triggering_event.child(type="trace.captured", payload=trace)
        )
