"""AI Flywheel — bottom-up, event-driven venture operating system.

This package is **Layer 1**: venture-agnostic, reusable capabilities.

Per the dependency rule in ``new_docs/README.md``:

    Layer 2 (ventures)     ──may import──▶  Layer 1 (capabilities)
    Layer 1 (capabilities) ──must NEVER import──▶ Layer 2 (ventures)

Nothing in this package may import a venture.
"""
