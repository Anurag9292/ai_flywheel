"""``web-scraper-client`` — derived in PostlineAI's outbound lead-gen step.

A **library tool** (leaf I/O) that fetches a URL and returns its **extracted
text** (career pages, about pages, blog posts) plus best-effort structured
signals like contact emails. Distinct from ``web-search-client``: that one
*finds* URLs, this one *reads* them.

Real impl will wrap a managed scraping/extraction provider (e.g. Firecrawl,
ScrapingBee) behind the ``WebScraperClient`` Protocol. Fake-first per
``new_docs/stack.md``: the offline fake serves canned page text and runs a
small regex to surface contact emails, so ``lead-sourcer`` can run end-to-end
without network.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

# A lightweight email matcher — good enough to find ``careers@…`` /
# ``hiring@…`` strings on a career page. Not a strict RFC 5322 validator.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class ScrapedPage(BaseModel):
    """The structured slice we keep from a fetched page."""

    url: str = ""
    title: str = ""
    text: str = ""
    # Emails surfaced from the page text (deduplicated, order-preserving).
    emails: list[str] = Field(default_factory=list)


@runtime_checkable
class WebScraperClient(Protocol):
    def scrape(self, url: str) -> ScrapedPage: ...


class FakeWebScraperClient:
    """Offline scraper returning deterministic canned pages.

    Built specifically so the ``lead-sourcer`` demo can enrich a job posting
    with a career-page fetch without hitting the network. Unknown URLs return
    a generic placeholder page so the flow never blows up; emails are extracted
    via the same regex used in production.
    """

    def __init__(self, pages: dict[str, ScrapedPage] | None = None) -> None:
        self._pages = dict(pages or {})

    def scrape(self, url: str) -> ScrapedPage:
        page = self._pages.get(url)
        if page is None:
            text = f"Canned career page content for {url}."
            page = ScrapedPage(url=url, title=url, text=text)
        # Always (re)run email extraction so a caller-supplied fixture without
        # pre-computed emails still surfaces them.
        if not page.emails:
            page = page.model_copy(update={"emails": _extract_emails(page.text)})
        return page


def _extract_emails(text: str) -> list[str]:
    """Surface unique emails from a blob of page text, preserving first-seen order."""
    seen: list[str] = []
    for match in _EMAIL_RE.findall(text):
        if match not in seen:
            seen.append(match)
    return seen
