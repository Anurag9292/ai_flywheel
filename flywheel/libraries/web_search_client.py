"""``web-search-client`` — derived in PostlineAI Step 2.

A **library tool** (leaf I/O) wrapping a search API (Brave / Serper / Exa).
Functions only: ``search(query)`` and ``fetch(url)``. No events.

Fake-first per ``new_docs/stack.md``; the real httpx-backed impl swaps in behind
the ``WebSearchClient`` Protocol when desk research needs live results.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


@runtime_checkable
class WebSearchClient(Protocol):
    def search(self, query: str, limit: int = 5) -> list[SearchResult]: ...

    def fetch(self, url: str) -> str: ...


class FakeWebSearchClient:
    """Offline search client returning deterministic canned results.

    Seeded with a small fixture so the ``market-scanner`` node can run
    end-to-end. ``fetch`` returns canned page text per URL.
    """

    def __init__(
        self,
        results: dict[str, list[SearchResult]] | None = None,
        pages: dict[str, str] | None = None,
    ) -> None:
        self._results = results or {}
        self._pages = pages or {}

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        # Exact-match fixture, else a single generic placeholder result.
        hits = self._results.get(query)
        if hits is None:
            hits = [
                SearchResult(
                    title=f"Result for {query}",
                    url=f"https://example.com/{query.replace(' ', '-')}",
                    snippet=f"A page about {query}.",
                )
            ]
        return hits[:limit]

    def fetch(self, url: str) -> str:
        return self._pages.get(url, f"Canned page content for {url}.")
