"""Tests for the CrawlAgent (best-first focused crawler)."""

from __future__ import annotations

from flywheel.core.crawl_agent import CrawlAgent, CrawlResult, score_link
from flywheel.libraries.web_scraper_client import FakeWebScraperClient, Link, ScrapedPage


def _page(url: str, text: str, links: list[tuple[str, str]]) -> ScrapedPage:
    host = url.split("/")[2]
    return ScrapedPage(
        url=url,
        text=text,
        links=[
            Link(url=u, anchor=a, same_domain=(u.split("/")[2] == host))
            for u, a in links
        ],
    )


# A tiny linked site: home → {pricing, about, contact}; contact has the email.
_SITE = {
    "https://acme.com/": _page(
        "https://acme.com/",
        "Acme home. Lots of marketing copy here about our product.",
        [
            ("https://acme.com/pricing", "Pricing"),
            ("https://acme.com/about", "About us"),
            ("https://acme.com/contact", "Contact"),
            ("https://twitter.com/acme", "Twitter"),  # off-domain → ignored
        ],
    ),
    "https://acme.com/pricing": _page("https://acme.com/pricing", "Plans and prices.", []),
    "https://acme.com/about": _page(
        "https://acme.com/about", "About Acme — we help founders.", []
    ),
    "https://acme.com/contact": _page(
        "https://acme.com/contact", "Reach us at careers@acme.com any time.", []
    ),
}


def test_score_link_prefers_goal_keywords() -> None:
    contact = Link(url="https://x.com/contact", anchor="Contact", same_domain=True)
    pricing = Link(url="https://x.com/pricing", anchor="Pricing", same_domain=True)
    assert score_link(contact, depth=1) > score_link(pricing, depth=1)


def test_crawl_finds_email_best_first_and_stops() -> None:
    agent = CrawlAgent(FakeWebScraperClient(pages=_SITE))
    result = agent.crawl("https://acme.com/")
    assert isinstance(result, CrawlResult)
    assert result.emails == ["careers@acme.com"]
    assert result.stop_reason == "goal_met"
    # Best-first: it should have gone home → contact (high score), NOT wasted the
    # budget on /pricing first. So /pricing need not be visited at all.
    assert "https://acme.com/contact" in result.pages_visited
    assert "https://acme.com/pricing" not in result.pages_visited


def test_crawl_stays_on_domain() -> None:
    agent = CrawlAgent(FakeWebScraperClient(pages=_SITE))
    result = agent.crawl("https://acme.com/")
    assert all("acme.com" in u for u in result.pages_visited)
    assert all("twitter.com" not in u for u in result.pages_visited)


def test_crawl_respects_page_budget() -> None:
    # No email anywhere → crawl until the page budget, then stop.
    site = {
        "https://acme.com/": _page(
            "https://acme.com/",
            "home",
            [
                ("https://acme.com/a", "about"),
                ("https://acme.com/b", "team"),
                ("https://acme.com/c", "careers"),
            ],
        ),
        "https://acme.com/a": _page("https://acme.com/a", "no email a", []),
        "https://acme.com/b": _page("https://acme.com/b", "no email b", []),
        "https://acme.com/c": _page("https://acme.com/c", "no email c", []),
    }
    agent = CrawlAgent(FakeWebScraperClient(pages=site), max_pages=2)
    result = agent.crawl("https://acme.com/")
    assert result.pages_count == 2
    assert result.stop_reason == "budget_pages"


def test_crawl_dedupes_visited() -> None:
    # Two pages that link to each other → must not loop forever.
    site = {
        "https://acme.com/": _page(
            "https://acme.com/", "home", [("https://acme.com/x", "about")]
        ),
        "https://acme.com/x": _page(
            "https://acme.com/x", "x", [("https://acme.com/", "home")]
        ),
    }
    agent = CrawlAgent(FakeWebScraperClient(pages=site), max_pages=10)
    result = agent.crawl("https://acme.com/")
    assert sorted(result.pages_visited) == ["https://acme.com/", "https://acme.com/x"]


def test_crawl_failure_is_non_fatal() -> None:
    class _Boom:
        def scrape(self, url: str) -> ScrapedPage:
            raise RuntimeError("network down")

    agent = CrawlAgent(_Boom())
    result = agent.crawl("https://acme.com/")
    # No crash; empty result with a sane stop reason.
    assert result.emails == []
    assert result.pages_count == 0


def test_crawl_captures_company_context() -> None:
    agent = CrawlAgent(FakeWebScraperClient(pages=_SITE))
    result = agent.crawl("https://acme.com/")
    assert "Acme" in result.company_context
