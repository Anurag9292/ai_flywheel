"""``CrawlAgent`` — a hand-rolled, best-first focused crawler.

The "GraphAgent" ``new_docs/stack.md`` anticipated: a stateful multi-step loop
that *navigates* a site (follow ``<a href>`` links best-first) to satisfy an
information goal, rather than scraping a single URL. See
``new_docs/scraping-engine.md`` for the architecture + the research it draws on
(focused/best-first crawling, planner/executor/aggregator, goal-conditioned
stop, graph memory).

It sits on the ``WebScraperClient`` Protocol (the swappable executor leaf), so it
is provider-agnostic: ``Fake`` for tests, ``Httpx`` in-house, ``Firecrawl`` for
JS-heavy pages — the crawler never knows which.

Phase 1: heuristic frontier (keyword/URL scoring), no LLM cost, no browser.
LLM link-scoring (neural crawling) and a browser executor are later phases.
"""

from __future__ import annotations

import heapq
import itertools
import time
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from flywheel.libraries.web_scraper_client import (
    FakeWebScraperClient,
    Link,
    ScrapedPage,
    WebScraperClient,
)

# Anchor/URL keywords that suggest a link leads to contact / positioning info.
# Each adds to a link's frontier priority (best-first).
_GOAL_KEYWORDS = (
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


class CrawlResult(BaseModel):
    """Structured outcome of a crawl (rides into the trace payload)."""

    seed_url: str = ""
    emails: list[str] = Field(default_factory=list)
    # Best positioning/context snippet found (longest meaningful page text).
    company_context: str = ""
    pages_visited: list[str] = Field(default_factory=list)
    stop_reason: str = ""  # "goal_met" | "budget_pages" | "frontier_empty" | "error"
    pages_count: int = 0


def score_link(link: Link, depth: int) -> float:
    """Best-first priority for a discovered link (heuristic, Phase 1).

    Higher = crawl sooner. Off-domain links are rejected by the caller; here we
    reward goal keywords in the URL/anchor and gently penalise deep paths.
    """
    blob = f"{link.url} {link.anchor}".lower()
    score = 0.1
    for kw in _GOAL_KEYWORDS:
        if kw in blob:
            score += 1.0
    score -= 0.05 * urlparse(link.url).path.count("/")
    score -= 0.2 * depth
    return score


class CrawlAgent:
    """Best-first focused crawler over a company site.

    Frontier = a max-priority queue of ``(score, url, depth)``. We pop the most
    promising URL, scrape it via the injected ``WebScraperClient``, absorb its
    findings (emails + a positioning snippet), and enqueue its same-domain links
    scored by :func:`score_link`. Stops on goal (an email found, when
    ``want_email``) or any budget. Best-effort: a page that fails to scrape is
    skipped, never fatal.
    """

    def __init__(
        self,
        scraper: WebScraperClient | None = None,
        *,
        max_pages: int = 8,
        max_depth: int = 2,
        time_limit_s: float = 30.0,
        min_link_score: float = 0.2,
        want_email: bool = True,
        snippet_chars: int = 600,
    ) -> None:
        self._scraper = scraper or FakeWebScraperClient()
        self._max_pages = max_pages
        self._max_depth = max_depth
        self._time_limit_s = time_limit_s
        self._min_link_score = min_link_score
        self._want_email = want_email
        self._snippet_chars = snippet_chars

    def crawl(self, seed_url: str) -> CrawlResult:
        root = urlparse(seed_url).netloc
        counter = itertools.count()  # tie-breaker → stable heap ordering
        # Python heapq is a min-heap; push negative score for max-first.
        frontier: list[tuple[float, int, str, int]] = []
        heapq.heappush(frontier, (-1.0, next(counter), seed_url, 0))

        visited: set[str] = set()
        emails: list[str] = []
        best_context = ""
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

            neg_score, _, url, depth = heapq.heappop(frontier)
            if url in visited:
                continue
            visited.add(url)

            try:
                page = self._scraper.scrape(url)
            except Exception:  # noqa: BLE001 — one bad page must not kill the crawl
                continue

            pages.append(url)
            for em in page.emails:
                if em not in emails:
                    emails.append(em)
            if len(page.text) > len(best_context):
                best_context = page.text[: self._snippet_chars]

            if self._want_email and emails:
                stop_reason = "goal_met"
                break
            if depth >= self._max_depth:
                continue

            for link, score in self._rank_links(page, root, depth, visited):
                heapq.heappush(frontier, (-score, next(counter), link.url, depth + 1))

        return CrawlResult(
            seed_url=seed_url,
            emails=emails,
            company_context=best_context,
            pages_visited=pages,
            pages_count=len(pages),
            stop_reason=stop_reason,
        )

    def _rank_links(
        self, page: ScrapedPage, root: str, depth: int, visited: set[str]
    ) -> list[tuple[Link, float]]:
        ranked: list[tuple[Link, float]] = []
        for link in page.links:
            if not link.same_domain and urlparse(link.url).netloc != root:
                continue
            if link.url in visited:
                continue
            s = score_link(link, depth)
            if s >= self._min_link_score:
                ranked.append((link, s))
        ranked.sort(key=lambda pair: pair[1], reverse=True)
        return ranked
