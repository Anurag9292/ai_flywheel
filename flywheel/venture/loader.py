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
    ingestion_stores_override: object | None = None,
) -> tuple[Runtime, InMemoryEventBus, TraceRecorder]:
    """Wire a Runtime by registering the venture's (deduplicated) node set.

    Returns the runtime, its bus, and the recorder — same shape as the old
    ``build_runtime()`` so callers (dev API, demos, tests) are unaffected.

    ``ingestion_stores_override`` (a bundle returned by ``reset_ingestion_stores``)
    backs the ingestion cluster with real (Neon) stores instead of fresh
    in-memory fakes. When ``None`` (default) the cluster uses fresh fakes, so
    demos/tests stay zero-infra and deterministic.
    """
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=trace_log, keep_in_memory=keep_in_memory)
    runtime = Runtime(bus, recorder)

    # Shared stores for the ingestion cluster. Each runtime build is isolated:
    # either fresh fakes (default) or the injected real-store bundle, so the
    # registry/scraper/builder/insight nodes all wire to the same instances.
    if ingestion_stores_override is not None:
        reset_ingestion_stores(
            source=ingestion_stores_override.source,  # type: ignore[attr-defined]
            raw=ingestion_stores_override.raw,  # type: ignore[attr-defined]
            knowledge=ingestion_stores_override.knowledge,  # type: ignore[attr-defined]
        )
    else:
        reset_ingestion_stores()

    for spec in venture.node_specs():
        runtime.register(build_node(spec.name, spec.config))

    return runtime, bus, recorder
