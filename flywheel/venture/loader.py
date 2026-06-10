"""Load a venture from YAML and build a Runtime from it.

This replaces the previously-hardcoded node registration in
``flywheel/devserver/topology.py``: the venture file is now the source of truth
for *which* nodes a venture runs (organized into functions), and this loader
turns that declaration into a live ``Runtime``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from flywheel.core.events import InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.venture.registry import build_node, reset_ingestion_stores
from flywheel.venture.schema import Venture

# Repo-root ``ventures/`` directory (this file is flywheel/venture/loader.py).
VENTURES_DIR = Path(__file__).resolve().parents[2] / "ventures"


def load_venture(path: str | Path) -> Venture:
    """Parse a venture YAML file into a validated :class:`Venture`."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Venture.model_validate(data)


def load_venture_by_name(name: str) -> Venture:
    """Load ``ventures/<name>.yaml``."""
    return load_venture(VENTURES_DIR / f"{name}.yaml")


def build_runtime_from_venture(
    venture: Venture,
    trace_log: Path | None = None,
    *,
    keep_in_memory: bool = False,
) -> tuple[Runtime, InMemoryEventBus, TraceRecorder]:
    """Wire a Runtime by registering the venture's (deduplicated) node set.

    Returns the runtime, its bus, and the recorder — same shape as the old
    ``build_runtime()`` so callers (dev API, demos, tests) are unaffected.
    """
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=trace_log, keep_in_memory=keep_in_memory)
    runtime = Runtime(bus, recorder)

    # Fresh shared stores for the ingestion cluster, so each runtime build is
    # isolated (the scraper/builder/registry nodes wire to this same bundle).
    reset_ingestion_stores()

    for spec in venture.node_specs():
        runtime.register(build_node(spec.name, spec.config))

    return runtime, bus, recorder
