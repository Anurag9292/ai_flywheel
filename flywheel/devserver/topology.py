"""Builds the runtime used by the dev introspection server.

The runtime is now **derived from a venture definition** (``ventures/postlineai.yaml``)
rather than a hardcoded node list — that file declares which Layer 1 nodes the
venture runs, organized into functions. See ``flywheel/venture/``.

``build_runtime()`` is kept (same signature) as the default entry point so the
dev API, demos, and tests are unaffected: it loads the PostlineAI venture and
builds a runtime from it. The agentic nodes default to canned fake gateways (via
the registry) so a triggered ``research.requested`` / ``campaign.requested`` runs
deterministically — real bus + real nodes, fake leaf I/O.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.core.events import InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.human_review_queue import HumanReviewQueue
from flywheel.venture.loader import build_runtime_from_venture, load_venture_by_name
from flywheel.venture.schema import Venture

DEFAULT_TRACE_LOG = Path("traces.jsonl")
DEFAULT_VENTURE = "postlineai"


def load_default_venture() -> Venture:
    """Load the default (PostlineAI) venture definition."""
    return load_venture_by_name(DEFAULT_VENTURE)


def build_runtime(
    trace_log: Path | None = None,
    *,
    keep_in_memory: bool = False,
) -> tuple[Runtime, InMemoryEventBus, TraceRecorder]:
    """Wire a Runtime from the default venture definition.

    Returns the runtime, its bus (so the API can publish onto it), and the
    recorder (so the API can read live in-memory traces / reset them).

    Pass ``trace_log`` to also append rows to a JSONL file (headless scripts);
    the dev API uses ``keep_in_memory=True`` and no file.
    """
    venture = load_default_venture()
    return build_runtime_from_venture(
        venture, trace_log, keep_in_memory=keep_in_memory
    )


def find_review_queue(runtime: Runtime) -> HumanReviewQueue | None:
    """Return the registered human-review-queue, if any (for the dev review API)."""
    for node in runtime.nodes:
        if isinstance(node, HumanReviewQueue):
            return node
    return None
