"""``web-scraper-client`` — derived in PostlineAI's outbound lead-gen step.

A **library tool** (leaf I/O) that fetches a URL and returns its **extracted
text + links** (career pages, about pages, etc.) plus best-effort structured
signals like contact emails. Distinct from ``web-search-client``: that one
*finds* URLs, this one *reads* them. It is the swappable **executor leaf** under
the ``CrawlAgent`` (see ``new_docs/scraping-engine.md``).

Three implementations behind the ``WebScraperClient`` Protocol:

- ``FakeWebScraperClient`` — deterministic canned pages (default; offline tests).
- ``HttpxScraperClient`` — **in-house, no browser.** Plain ``httpx`` GET → strip
  scripts/tags → visible text + ``<a href>`` extraction + email regex. Handles
  the SSR pages that make up most company sites; drops the hard Firecrawl
  dependency. (JS-rendered pages are the deferred Playwright/Firecrawl case.)
- ``FirecrawlScraperClient`` — managed provider for JS-heavy / anti-bot pages.

All three populate ``ScrapedPage.links`` so the ``CrawlAgent`` can follow them
best-first.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field

# A lightweight email matcher — good enough to find ``careers@…`` /
# ``hiring@…`` strings on a page. Not a strict RFC 5322 validator.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class Link(BaseModel):
    """One outgoing link found on a page (the crawl frontier feeds on these)."""

    url: str = ""
    anchor: str = ""  # visible anchor text (or a slug derived from the href)
    same_domain: bool = False


class ScrapedPage(BaseModel):
    """The structured slice we keep from a fetched page."""

    url: str = ""
    title: str = ""
    text: str = ""
    # Emails surfaced from the page text (deduplicated, order-preserving).
    emails: list[str] = Field(default_factory=list)
    # Outgoing links (for the CrawlAgent frontier). Empty for a single-page scrape.
    links: list[Link] = Field(default_factory=list)


@runtime_checkable
class WebScraperClient(Protocol):
    def scrape(self, url: str) -> ScrapedPage: ...


# ── HTML parsing helpers (shared by httpx executor + fakes) ───────────────────


class _HtmlExtractor(HTMLParser):
    """Pulls visible text + ``<a href>`` links + ``<title>`` from raw HTML.

    Deliberately dependency-free (stdlib ``html.parser``) so the in-house
    executor needs no bs4/lxml. Skips script/style content for clean text.
    """

    _SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._text_parts: list[str] = []
        # (href, anchor-text-accumulator)
        self._links: list[tuple[str, list[str]]] = []
        self._open_link: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            if href:
                acc: list[str] = []
                self._links.append((href, acc))
                self._open_link = acc

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "a":
            self._open_link = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
        if self._open_link is not None:
            self._open_link.append(data)
        self._text_parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self._text_parts).split())

    def links(self, base_url: str) -> list[Link]:
        base_host = urlparse(base_url).netloc
        out: list[Link] = []
        seen: set[str] = set()
        for href, acc in self._links:
            href = href.strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(base_url, href)
            if not absolute.startswith(("http://", "https://")):
                continue
            absolute = absolute.split("#")[0]
            if absolute in seen:
                continue
            seen.add(absolute)
            anchor = " ".join(" ".join(acc).split()) or href.rsplit("/", 1)[-1].replace("-", " ")
            out.append(
                Link(
                    url=absolute,
                    anchor=anchor[:120],
                    same_domain=urlparse(absolute).netloc == base_host,
                )
            )
        return out


def parse_html(html: str, base_url: str) -> ScrapedPage:
    """Parse raw HTML into a ``ScrapedPage`` (text + links + emails)."""
    extractor = _HtmlExtractor()
    try:
        extractor.feed(html)
    except Exception:  # noqa: BLE001 — malformed HTML must never crash a crawl
        pass
    text = extractor.text
    return ScrapedPage(
        url=base_url,
        title=" ".join(extractor.title.split())[:200] or base_url,
        text=text,
        emails=_extract_emails(text),
        links=extractor.links(base_url),
    )


class FakeWebScraperClient:
    """Offline scraper returning deterministic canned pages.

    Built so the ``lead-sourcer`` demo + tests can crawl without network. A
    fixture may be a ``ScrapedPage`` (with canned links) or a raw HTML string
    (parsed via :func:`parse_html`, so fakes can exercise link extraction too).
    Unknown URLs return a generic placeholder page so the flow never blows up.
    """

    def __init__(self, pages: dict[str, ScrapedPage | str] | None = None) -> None:
        self._pages: dict[str, ScrapedPage | str] = dict(pages or {})

    def scrape(self, url: str) -> ScrapedPage:
        raw = self._pages.get(url)
        if isinstance(raw, str):
            return parse_html(raw, url)
        if isinstance(raw, ScrapedPage):
            page = raw
        else:
            text = f"Canned career page content for {url}."
            page = ScrapedPage(url=url, title=url, text=text)
        if not page.emails:
            page = page.model_copy(update={"emails": _extract_emails(page.text)})
        return page


class HttpxScraperClient:
    """In-house executor: plain ``httpx`` GET → text + links + emails (no browser).

    Handles server-rendered (SSR) pages — the majority of company marketing /
    about / contact / careers pages. JS-rendered pages (empty/thin body) are the
    deferred browser-backed case (Firecrawl / Playwright). Imports ``httpx``
    lazily and is polite (UA, timeout, retries, max-bytes guard).
    """

    _UA = "ai-flywheel-crawl/0.1 (+postlineai lead-gen; contact via site)"

    def __init__(self, *, timeout: float = 15.0, max_bytes: int = 3_000_000) -> None:
        self._timeout = timeout
        self._max_bytes = max_bytes

    def scrape(self, url: str) -> ScrapedPage:
        import httpx
        from tenacity import (
            retry,
            retry_if_exception_type,
            stop_after_attempt,
            wait_exponential,
        )

        @retry(
            retry=retry_if_exception_type(httpx.HTTPError),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, max=4),
            reraise=True,
        )
        def _get() -> str:
            resp = httpx.get(
                url,
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": self._UA},
            )
            resp.raise_for_status()
            return resp.text[: self._max_bytes]

        return parse_html(_get(), url)


class FirecrawlScraperClient:
    """Managed scraper backed by Firecrawl — for JS-heavy / anti-bot pages.

    Reads ``FIRECRAWL_API_KEY`` from the environment (or takes an explicit key).
    The ``firecrawl-py`` SDK is imported lazily. The ``client`` is injectable so
    tests can drive it with a stub and zero network. Now also returns ``links``
    (parsed from the returned markdown) so it can back the ``CrawlAgent`` too.
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
            from firecrawl import Firecrawl  # type: ignore[import-not-found]

            self._client = Firecrawl(api_key=self._api_key)
        return self._client

    def scrape(self, url: str) -> ScrapedPage:
        client = self._get_client()
        doc: Any = client.scrape(url, formats=["markdown", "links"])  # type: ignore[attr-defined]
        text = _read_field(doc, "markdown") or _read_field(doc, "text") or ""
        title = _read_field(_read_field(doc, "metadata") or {}, "title") or url
        # Firecrawl returns absolute links; tag same-domain so the crawler can
        # stay on the company site.
        base_host = urlparse(url).netloc
        links: list[Link] = []
        for href in _read_field(doc, "links") or []:
            if not isinstance(href, str) or not href.startswith(("http://", "https://")):
                continue
            links.append(
                Link(
                    url=href.split("#")[0],
                    anchor=href.rsplit("/", 1)[-1].replace("-", " ")[:120],
                    same_domain=urlparse(href).netloc == base_host,
                )
            )
        return ScrapedPage(
            url=url, title=title, text=text, emails=_extract_emails(text), links=links
        )


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
