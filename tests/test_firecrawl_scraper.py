"""Tests for the opt-in Firecrawl scraper + the LeadStore (no network)."""

from __future__ import annotations

from typing import Any

from flywheel.libraries.lead_store import InMemoryLeadStore, LeadStore
from flywheel.libraries.web_scraper_client import (
    FirecrawlScraperClient,
    WebScraperClient,
)

# ── LeadStore ─────────────────────────────────────────────────────────────────


def test_in_memory_lead_store_dedup() -> None:
    store = InMemoryLeadStore()
    assert store.seen("https://x/1") is False
    store.mark_seen("https://x/1")
    assert store.seen("https://x/1") is True
    assert len(store) == 1


def test_in_memory_lead_store_ignores_empty_url() -> None:
    store = InMemoryLeadStore()
    store.mark_seen("")  # no-op
    assert store.seen("") is False
    assert len(store) == 0


def test_lead_store_protocol_satisfied() -> None:
    assert isinstance(InMemoryLeadStore(), LeadStore)


# ── FirecrawlScraperClient (injected stub client, zero network) ───────────────


class _StubFirecrawl:
    """Mimics the firecrawl SDK's .scrape() returning a dict with markdown."""

    def __init__(self, markdown: str) -> None:
        self._markdown = markdown

    def scrape(self, url: str, formats: list[str] | None = None) -> dict[str, Any]:
        return {
            "markdown": self._markdown,
            "metadata": {"title": "Careers @ Acme"},
        }


def test_firecrawl_scraper_returns_scraped_page_with_emails() -> None:
    stub = _StubFirecrawl("Join us! Email careers@acme.com or hiring@acme.com.")
    client = FirecrawlScraperClient(client=stub)
    page = client.scrape("https://acme.example.com/careers")
    assert page.url == "https://acme.example.com/careers"
    assert page.title == "Careers @ Acme"
    assert page.emails == ["careers@acme.com", "hiring@acme.com"]


def test_firecrawl_scraper_satisfies_protocol() -> None:
    assert isinstance(FirecrawlScraperClient(client=_StubFirecrawl("x")), WebScraperClient)


def test_firecrawl_from_env_is_opt_in(monkeypatch: Any) -> None:
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    assert FirecrawlScraperClient.from_env() is None
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    assert isinstance(FirecrawlScraperClient.from_env(), FirecrawlScraperClient)
