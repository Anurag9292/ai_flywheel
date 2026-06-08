"""Layer 2 — **Venture composition** (the venture definition file).

A venture is *not* a forked codebase (``new_docs/vision.md`` principle 4). It is,
in order of preference:

1. a **topology** — which Layer 1 nodes are active, wired by events, with config,
2. **domain assets** — thesis, ICP, prompts,
3. a small ``custom/`` escape hatch (deferred — not built yet).

This package makes that concrete: a YAML file (``ventures/<name>.yaml``) declares
the venture, and the loader builds a runtime from it — replacing the previously
hardcoded ``build_runtime()`` registration list.

**Functions** are a *declarative grouping* layer inside a venture: a named bundle
of nodes (marketing, gtm, customer-success…) that exists for composition and
legibility. A function is metadata + a topology fragment — it groups nodes and
labels the events they own. **It does not orchestrate**: events still flow
node→node via the bus exactly as before. Functions may overlap (a node can
belong to several); none owns a node exclusively.
"""

from flywheel.venture.schema import FunctionSpec, NodeSpec, Venture

__all__ = ["Venture", "FunctionSpec", "NodeSpec"]
