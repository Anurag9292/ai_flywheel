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

import os
from pathlib import Path

from flywheel.core.events import InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.human_review_queue import HumanReviewQueue
from flywheel.venture.loader import build_runtime_from_venture, load_venture_by_name
from flywheel.venture.schema import Venture

DEFAULT_TRACE_LOG = Path("traces.jsonl")
DEFAULT_VENTURE = "postlineai"
# Env var that selects which venture definition the dev server loads. Default is
# the offline/fake ``postlineai``; set ``FLYWHEEL_VENTURE=postlineai-live`` to run
# the SAME UI against real public ATS discovery (see ventures/postlineai-live.yaml).
VENTURE_ENV_VAR = "FLYWHEEL_VENTURE"


def selected_venture_name() -> str:
    """Which venture the dev server should load (env-overridable)."""
    return os.environ.get(VENTURE_ENV_VAR, DEFAULT_VENTURE) or DEFAULT_VENTURE


def load_default_venture(name: str | None = None) -> Venture:
    """Load a venture definition by name (defaults to the env-selected one)."""
    return load_venture_by_name(name or selected_venture_name())


def runtime_mode(venture: Venture) -> str:
    """Report whether lead-gen discovery is ``"live"`` (real ATS) or ``"fake"``.

    Derived honestly from the venture's own composition: if any ``lead-sourcer``
    node is declared with ``config.live == True``, the runtime is live. This is
    what the ``/topology`` LIVE/FAKE badge reads.
    """
    for spec in venture.node_specs():
        if spec.name == "lead-sourcer" and spec.config.get("live", False):
            return "live"
    return "fake"


def build_runtime(
    trace_log: Path | None = None,
    *,
    keep_in_memory: bool = False,
    venture_name: str | None = None,
) -> tuple[Runtime, InMemoryEventBus, TraceRecorder]:
    """Wire a Runtime from a venture definition (env-selected by default).

    Returns the runtime, its bus (so the API can publish onto it), and the
    recorder (so the API can read live in-memory traces / reset them).

    ``venture_name`` overrides the selection; otherwise ``FLYWHEEL_VENTURE`` (or
    the ``postlineai`` default) decides. Backward compatible: callers that pass
    nothing get the default offline venture exactly as before.

    Pass ``trace_log`` to also append rows to a JSONL file (headless scripts);
    the dev API uses ``keep_in_memory=True`` and no file.
    """
    venture = load_default_venture(venture_name)
    return build_runtime_from_venture(
        venture, trace_log, keep_in_memory=keep_in_memory
    )


def find_review_queue(runtime: Runtime) -> HumanReviewQueue | None:
    """Return the registered human-review-queue, if any (for the dev review API)."""
    for node in runtime.nodes:
        if isinstance(node, HumanReviewQueue):
            return node
    return None
