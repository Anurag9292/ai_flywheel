"""``analytics-client`` — derived in PostlineAI Step 4.

A **library tool** (leaf I/O) wrapping a landing-page analytics API
(PostHog / Plausible) used to read signups/conversions on the landing page the
ad test points at. Pure function calls; no events.

Fake-first per ``new_docs/stack.md``; the real impl swaps in behind the
``AnalyticsClient`` Protocol when live landing-page data is needed.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class LandingStats(BaseModel):
    page: str
    visitors: int = 0
    signups: int = 0


@runtime_checkable
class AnalyticsClient(Protocol):
    def landing_stats(self, page: str) -> LandingStats: ...


class FakeAnalyticsClient:
    """Offline analytics client returning deterministic canned stats."""

    def __init__(self, fixtures: dict[str, LandingStats] | None = None) -> None:
        self._fixtures = fixtures or {}

    def landing_stats(self, page: str) -> LandingStats:
        if page in self._fixtures:
            return self._fixtures[page]
        seed = sum(ord(c) for c in page)
        visitors = (seed * 7) % 2_000
        return LandingStats(
            page=page,
            visitors=visitors,
            signups=visitors // 20,
        )
