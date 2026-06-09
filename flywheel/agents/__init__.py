"""Composite, Agent-style Layer 1 capabilities (vs. leaf ``libraries/``).

These are reusable capabilities that *compose* leaf tools into multi-step
behaviour — e.g. the goal-agnostic :class:`CrawlAgent`, which navigates a site
via the ``WebScraperClient`` leaf toward a pluggable :class:`CrawlGoal`. They are
venture-agnostic Layer 1 (see ``new_docs/README.md``), not substrate (``core/``).
"""
