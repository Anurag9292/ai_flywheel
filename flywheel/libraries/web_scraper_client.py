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
from typing import Any, Protocol, runtime_checkable

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


class FirecrawlScraperClient:
    """Real career-page scraper backed by Firecrawl (OPT-IN).

    This is the *only* potentially-paid piece of lead-gen. Discovery via the ATS
    APIs is free; this enrichment layer is invoked by ``lead-sourcer`` **only
    when a posting lacks a contact email**, so on a curated roster it stays well
    within Firecrawl's free tier.

    Reads ``FIRECRAWL_API_KEY`` from the environment (or takes an explicit key).
    The ``firecrawl-py`` SDK is imported lazily so nothing requires it unless a
    venture actually wires this client in. The ``client`` is injectable purely so
    tests can drive it with a stub and zero network.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: object | None = None,
    ) -> None:
        self._injected = client
        self._api_key = api_key
        self._client = client  # may be set lazily on first scrape

    @classmethod
    def from_env(cls) -> FirecrawlScraperClient | None:
        """Build from ``FIRECRAWL_API_KEY`` if present, else ``None`` (opt-in)."""
        import os

        key = os.environ.get("FIRECRAWL_API_KEY")
        return cls(api_key=key) if key else None

    def _get_client(self) -> object:
        if self._client is None:
            # lazy import: only when actually scraping live. The SDK is an
            # optional dep (the ``lead-gen`` extra) so mypy can't see it in the
            # default/dev env — ignore the missing stub.
            from firecrawl import Firecrawl  # type: ignore[import-not-found]

            self._client = Firecrawl(api_key=self._api_key)
        return self._client

    def scrape(self, url: str) -> ScrapedPage:
        client = self._get_client()
        # SDK returns an object/dict with markdown + metadata. We read defensively
        # so a minor SDK shape change can't crash the lead-gen run.
        doc: Any = client.scrape(url, formats=["markdown"])  # type: ignore[attr-defined]
        text = _read_field(doc, "markdown") or _read_field(doc, "text") or ""
        title = _read_field(_read_field(doc, "metadata") or {}, "title") or url
        return ScrapedPage(url=url, title=title, text=text, emails=_extract_emails(text))


def _read_field(obj: Any, name: str) -> Any:
    """Read ``name`` from a dict or an attribute-style object (SDK-agnostic)."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _extract_emails(text: str) -> list[str]:
    """Surface unique emails from a blob of page text, preserving first-seen order."""
    seen: list[str] = []
    for match in _EMAIL_RE.findall(text):
        if match not in seen:
            seen.append(match)
    return seen
