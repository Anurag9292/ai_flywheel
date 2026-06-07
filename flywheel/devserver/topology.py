"""Builds the runtime used by the dev introspection server.

It registers the nodes that exist today (Step 1 + Step 2) so ``describe()``
returns a meaningful graph. As new nodes are built, register them here (or, once
``topology.yaml`` exists in Layer 2, derive this from a venture topology).
"""

from __future__ import annotations

from pathlib import Path

from flywheel.core.events import InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.market_scanner import MarketScanner
from flywheel.nodes.thesis_tracker import ThesisTracker

DEFAULT_TRACE_LOG = Path("traces.jsonl")


def build_runtime(trace_log: Path | None = None) -> Runtime:
    """Wire a Runtime with all currently-built nodes registered."""
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=trace_log or DEFAULT_TRACE_LOG)
    runtime = Runtime(bus, recorder)

    runtime.register(ThesisTracker())
    runtime.register(MarketScanner())

    return runtime
