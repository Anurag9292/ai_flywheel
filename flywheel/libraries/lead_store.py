"""``lead-store`` — dedup + cache seam for outbound lead-gen.

A **library tool** (leaf I/O) that remembers which postings we've already seen,
so a live ``MultiATSJobBoardClient`` run doesn't surface (and ultimately
re-pitch) the same company/role on every scan. Pure function calls; no events.

Per ``new_docs/stack.md`` lazy-arrival doctrine, the thin first impl is
in-memory (``InMemoryLeadStore``). The durable Postgres/Neon impl is the
documented *next* slice — it swaps in behind this same ``LeadStore`` Protocol
with no change to the ATS clients or the ``lead-sourcer`` node.

> **Scope (deliberate):** today this is per-process and resets on restart. That
> is enough to dedup *within* a run / a long-lived dev process. "Already
> pitched, ever" memory wants the durable impl — see the deferral note.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LeadStore(Protocol):
    """Tracks which posting URLs have been surfaced before (dedup)."""

    def seen(self, url: str) -> bool: ...

    def mark_seen(self, url: str) -> None: ...


class InMemoryLeadStore:
    """Process-local dedup set. Resets on restart (thin first impl).

    ``url`` is the natural dedup key: every ATS gives each posting a stable,
    unique hosted URL, and ``lead-sourcer`` already treats URL as the identity
    of a posting. Empty URLs are never considered "seen" (we can't dedup what we
    can't key) so they always pass through.
    """

    def __init__(self, seen: set[str] | None = None) -> None:
        self._seen: set[str] = set(seen or set())

    def seen(self, url: str) -> bool:
        return bool(url) and url in self._seen

    def mark_seen(self, url: str) -> None:
        if url:
            self._seen.add(url)

    def __len__(self) -> int:
        return len(self._seen)
