"""Dev-only introspection server.

> **This is not the venture runtime and not a production API.** It is a
> read-only, local-only surface that exposes ``Runtime.describe()`` and the
> ``trace.captured`` stream so the frontend topology map / trace replay
> (``new_docs/visualization.md``) can render the *real* system instead of
> hand-authored data.
>
> ``new_docs/stack.md`` defers standing up a backend HTTP service; this is the
> narrow, deliberate exception called out in ``visualization.md``.
"""
