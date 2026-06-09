"""``CrawlAgent`` — a goal-agnostic, best-first focused crawler (Layer 1 capability).

A reusable, venture-agnostic capability (not substrate — it lives in
``flywheel/agents/``, not ``core/``). It *navigates* a site — following
``<a href>`` links best-first — toward a pluggable :class:`CrawlGoal`, rather
than scraping a single URL. The "GraphAgent" ``new_docs/stack.md`` anticipated.
See ``new_docs/scraping-engine.md`` for the architecture + the research it draws
on (focused/best-first crawling, planner/executor/aggregator, goal-conditioned
stop, graph memory).

**Separation of concerns (the whole point):**

- ``CrawlAgent`` owns the *mechanism* — the frontier (priority queue), budgets,
  visited-set dedupe, same-domain restriction. 100% generic.
- A ``CrawlGoal`` owns the *intent* — how to score links, what to accumulate,
  when to stop, and what to extract. Swap the goal → reuse the crawler for any
  use case (lead-gen contact discovery, market research, RAG ingestion, …).

It sits on the ``WebScraperClient`` Protocol (the swappable executor leaf), so it
is provider-agnostic too: ``Fake`` for tests, ``Httpx`` in-house, ``Firecrawl``
for JS-heavy pages — the crawler never knows which.
"""

from __future__ import annotations

import heapq
import itertools
import time
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from flywheel.libraries.web_scraper_client import (
    FakeWebScraperClient,
    Link,
    ScrapedPage,
    WebScraperClient,
)


@runtime_checkable
class CrawlGoal(Protocol):
    """The pluggable *intent* of a crawl. The agent supplies the *mechanism*.

    Implementations decide what's worth crawling toward and what to keep. The
    agent calls ``score_link`` to prioritise the frontier, ``absorb`` on every
    fetched page, checks ``satisfied`` to stop early, and reads ``result`` at the
    end (merged into ``CrawlResult.findings``).
    """

    def score_link(self, link: Link, depth: int) -> float: ...

    def absorb(self, page: ScrapedPage) -> None: ...

    def satisfied(self) -> bool: ...

    def result(self) -> dict[str, Any]: ...


class CrawlResult(BaseModel):
    """Generic outcome of a crawl. Goal-specific output lives in ``findings``."""

    seed_url: str = ""
    pages_visited: list[str] = Field(default_factory=list)
    pages_count: int = 0
    # "goal_met" | "budget_pages" | "budget_time" | "frontier_empty"
    stop_reason: str = ""
    # Whatever the CrawlGoal extracted (e.g. {"emails": [...], "context": "..."}).
    findings: dict[str, Any] = Field(default_factory=dict)


# ── Shared scoring helper (goals can reuse it) ────────────────────────────────


def keyword_link_score(
    link: Link, depth: int, keywords: tuple[str, ...], *, base: float = 0.1
) -> float:
    """Best-first priority: reward goal keywords in URL/anchor, penalise depth."""
    blob = f"{link.url} {link.anchor}".lower()
    score = base
    for kw in keywords:
        if kw in blob:
            score += 1.0
    score -= 0.05 * urlparse(link.url).path.count("/")
    score -= 0.2 * depth
    return score


# ── Goal: contact discovery (lead-gen) ────────────────────────────────────────

_CONTACT_KEYWORDS = (
    "contact",
    "about",
    "team",
    "careers",
    "career",
    "company",
    "jobs",
    "press",
    "people",
    "who-we-are",
)


class ContactCrawlGoal:
    """Find a contact email + a company-positioning snippet (lead-gen).

    Scores contact/about/careers links highest, stops when an email is found,
    and extracts ``emails`` + ``context`` (longest page text seen). This is the
    lead-gen-specific intent, kept *out* of the generic crawler.
    """

    def __init__(self, *, snippet_chars: int = 600) -> None:
        self._snippet_chars = snippet_chars
        self.emails: list[str] = []
        self.context: str = ""

    def score_link(self, link: Link, depth: int) -> float:
        return keyword_link_score(link, depth, _CONTACT_KEYWORDS)

    def absorb(self, page: ScrapedPage) -> None:
        for em in page.emails:
            if em not in self.emails:
                self.emails.append(em)
        if len(page.text) > len(self.context):
            self.context = page.text[: self._snippet_chars]

    def satisfied(self) -> bool:
        return bool(self.emails)

    def result(self) -> dict[str, Any]:
        return {"emails": self.emails, "context": self.context}


# ── Goal: keyword/topic capture (e.g. market research) — proves reuse ─────────


class KeywordCrawlGoal:
    """Find pages matching target keywords; collect matching snippets.

    A second, venture-agnostic goal that demonstrates the crawler generalises
    beyond lead-gen: e.g. "find pricing / competitor / docs pages." Stops once
    ``min_matches`` matching pages are collected.
    """

    def __init__(
        self,
        keywords: list[str],
        *,
        min_matches: int = 3,
        snippet_chars: int = 400,
    ) -> None:
        self._keywords = tuple(k.lower() for k in keywords)
        self._min_matches = min_matches
        self._snippet_chars = snippet_chars
        self.matches: list[dict[str, str]] = []

    def score_link(self, link: Link, depth: int) -> float:
        return keyword_link_score(link, depth, self._keywords)

    def absorb(self, page: ScrapedPage) -> None:
        text_l = page.text.lower()
        hits = [kw for kw in self._keywords if kw in text_l]
        if hits:
            self.matches.append(
                {
                    "url": page.url,
                    "matched": ",".join(hits),
                    "snippet": page.text[: self._snippet_chars],
                }
            )

    def satisfied(self) -> bool:
        return len(self.matches) >= self._min_matches

    def result(self) -> dict[str, Any]:
        return {"matches": self.matches}


# ── The agent (mechanism only) ────────────────────────────────────────────────


class CrawlAgent:
    """Goal-agnostic best-first focused crawler.

    Frontier = a max-priority queue of ``(score, url, depth)``. Pop the most
    promising URL, scrape it via the injected ``WebScraperClient``, hand the page
    to the ``CrawlGoal`` (``absorb``), stop if ``satisfied`` or any budget is hit,
    else enqueue same-domain links scored by ``goal.score_link``. Best-effort: a
    page that fails to scrape is skipped, never fatal.
    """

    def __init__(
        self,
        scraper: WebScraperClient | None = None,
        *,
        max_pages: int = 8,
        max_depth: int = 2,
        time_limit_s: float = 30.0,
        min_link_score: float | None = None,
    ) -> None:
        self._scraper = scraper or FakeWebScraperClient()
        self._max_pages = max_pages
        self._max_depth = max_depth
        self._time_limit_s = time_limit_s
        # A floor that *prunes* links below it. Default ``None`` = no pruning:
        # best-first still crawls the highest-scored links first, but same-domain
        # links aren't *excluded* just because they don't match goal keywords
        # (their content may still match — the budget bounds exploration). Set a
        # value to aggressively prune low-signal links.
        self._min_link_score = min_link_score

    def crawl(self, seed_url: str, goal: CrawlGoal) -> CrawlResult:
        root = urlparse(seed_url).netloc
        counter = itertools.count()  # tie-breaker → stable heap ordering
        frontier: list[tuple[float, int, str, int]] = []
        heapq.heappush(frontier, (-1.0, next(counter), seed_url, 0))

        visited: set[str] = set()
        pages: list[str] = []
        started = time.monotonic()
        stop_reason = "frontier_empty"

        while frontier:
            if len(pages) >= self._max_pages:
                stop_reason = "budget_pages"
                break
            if time.monotonic() - started > self._time_limit_s:
                stop_reason = "budget_time"
                break

            _neg, _, url, depth = heapq.heappop(frontier)
            if url in visited:
                continue
            visited.add(url)

            try:
                page = self._scraper.scrape(url)
            except Exception:  # noqa: BLE001 — one bad page must not kill the crawl
                continue

            pages.append(url)
            goal.absorb(page)

            if goal.satisfied():
                stop_reason = "goal_met"
                break
            if depth >= self._max_depth:
                continue

            for link, score in self._rank_links(page, root, depth, visited, goal):
                heapq.heappush(frontier, (-score, next(counter), link.url, depth + 1))

        return CrawlResult(
            seed_url=seed_url,
            pages_visited=pages,
            pages_count=len(pages),
            stop_reason=stop_reason,
            findings=goal.result(),
        )

    def _rank_links(
        self,
        page: ScrapedPage,
        root: str,
        depth: int,
        visited: set[str],
        goal: CrawlGoal,
    ) -> list[tuple[Link, float]]:
        ranked: list[tuple[Link, float]] = []
        for link in page.links:
            if not link.same_domain and urlparse(link.url).netloc != root:
                continue
            if link.url in visited:
                continue
            s = goal.score_link(link, depth)
            if self._min_link_score is not None and s < self._min_link_score:
                continue
            ranked.append((link, s))
        ranked.sort(key=lambda pair: pair[1], reverse=True)
        return ranked


__all__ = [
    "CrawlAgent",
    "CrawlGoal",
    "CrawlResult",
    "ContactCrawlGoal",
    "KeywordCrawlGoal",
    "keyword_link_score",
]
