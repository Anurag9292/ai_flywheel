"""The venture-definition schema (Pydantic).

A ``Venture`` is the declarative description of one product living on the
platform: its domain assets, plus the **functions** (grouped node rosters) that
compose it. See ``flywheel/venture/__init__.py`` for the model and the firm rule
that functions are *declarative groupings, not orchestrators*.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    """One active node in a venture, with optional construction config.

    ``name`` matches a key in the node registry (``flywheel/venture/registry.py``).
    ``config`` is passed to that node's factory — e.g. ``{"impl": "human"}`` for
    ``post-drafter``, or a canned-gateway selector for an agentic demo node.

    Note: per-event *rubrics* (e.g. signal-analyzer's "would pay $499/mo") still
    travel in the event payload at runtime — they are not node config. ``config``
    is for construction-time bindings only.
    """

    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class FunctionSpec(BaseModel):
    """A named, declarative grouping of nodes (a department / capability area).

    Examples: ``market-exploration``, ``gtm``, ``customer-success``. A function
    groups nodes and (derived) the events they react to / emit. It performs **no
    orchestration** — it is metadata over the event graph. Nodes may appear in
    more than one function.
    """

    name: str
    description: str = ""
    nodes: list[NodeSpec] = Field(default_factory=list)


class Venture(BaseModel):
    """A full venture definition, normally loaded from ``ventures/<name>.yaml``."""

    name: str
    description: str = ""
    # Domain assets: thesis, ICP, price hypothesis, etc. Free-form for now;
    # tightened only when a node actually consumes a field (bottom-up rule).
    domain: dict[str, Any] = Field(default_factory=dict)
    functions: list[FunctionSpec] = Field(default_factory=list)

    def node_specs(self) -> list[NodeSpec]:
        """The deduplicated union of node specs across all functions.

        A node appearing in multiple functions is registered once. If the same
        node name appears with differing config, the *first* occurrence wins
        (and :meth:`lint` flags the conflict).
        """
        seen: dict[str, NodeSpec] = {}
        for fn in self.functions:
            for spec in fn.nodes:
                seen.setdefault(spec.name, spec)
        return list(seen.values())

    def functions_for(self, node_name: str) -> list[str]:
        """Which function(s) a node belongs to (overlap is allowed)."""
        return [fn.name for fn in self.functions if any(n.name == node_name for n in fn.nodes)]
