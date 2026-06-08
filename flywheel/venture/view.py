"""Function-aware projections over a venture + the live topology.

``Runtime.describe()`` (Layer 1) stays venture-agnostic — it only knows nodes,
events, and edges. This module is the Layer 2 lens: given a :class:`Venture` and
a ``describe()`` output, it groups the live graph **by function** and lints the
venture's *intended* composition against the *actual* code-derived graph.

Keeping this here (not in ``Runtime``) preserves the one-way dependency:
Layer 2 may read Layer 1, never the reverse.
"""

from __future__ import annotations

from typing import Any

from flywheel.venture.registry import known_node_names
from flywheel.venture.schema import Venture


def function_view(venture: Venture, describe: dict[str, Any]) -> list[dict[str, Any]]:
    """Group the live topology by function.

    For each function, returns its member nodes plus the (deduplicated, sorted)
    union of events those nodes react to and emit — i.e. the events the function
    "owns" as inputs/outputs. Derived from the live ``describe()`` so it can't
    drift from the code.
    """
    node_meta = {n["name"]: n for n in describe.get("nodes", [])}

    view: list[dict[str, Any]] = []
    for fn in venture.functions:
        events_in: set[str] = set()
        events_out: set[str] = set()
        members: list[str] = []
        for spec in fn.nodes:
            members.append(spec.name)
            meta = node_meta.get(spec.name)
            if meta is None:
                continue
            events_in.update(meta.get("reacts_to", []))
            events_out.update(meta.get("emits", []))
        view.append(
            {
                "name": fn.name,
                "description": fn.description,
                "nodes": members,
                "events_in": sorted(events_in),
                "events_out": sorted(events_out),
            }
        )
    return view


def lint_venture(venture: Venture, describe: dict[str, Any]) -> dict[str, Any]:
    """Cross-check the venture's intended composition vs. the live graph.

    Flags:
    - ``unknown_nodes`` — named in the venture file but absent from the registry.
    - ``inactive_nodes`` — in the venture but not actually registered in the
      runtime (shouldn't happen via the loader, but catches drift).
    - ``config_conflicts`` — same node named with differing config across
      functions (first wins; the rest are reported).
    - plus the Layer 1 ``orphan_emitted`` / ``unproduced_reacted`` passthrough.
    """
    registry = set(known_node_names())
    live_nodes = {n["name"] for n in describe.get("nodes", [])}

    named: list[str] = []
    config_seen: dict[str, Any] = {}
    config_conflicts: list[str] = []
    for fn in venture.functions:
        for spec in fn.nodes:
            named.append(spec.name)
            if spec.name in config_seen and config_seen[spec.name] != spec.config:
                config_conflicts.append(spec.name)
            else:
                config_seen.setdefault(spec.name, spec.config)

    unknown = sorted({n for n in named if n not in registry})
    inactive = sorted({n for n in named if n in registry and n not in live_nodes})

    layer1_lint = describe.get("lint", {})
    return {
        "unknown_nodes": unknown,
        "inactive_nodes": inactive,
        "config_conflicts": sorted(set(config_conflicts)),
        "orphan_emitted": layer1_lint.get("orphan_emitted", []),
        "unproduced_reacted": layer1_lint.get("unproduced_reacted", []),
    }
