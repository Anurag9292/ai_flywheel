"""Tests for the goal-agnostic CrawlAgent + the shipped CrawlGoals."""

from __future__ import annotations

from typing import Any

from flywheel.agents.crawl_agent import (
    ContactCrawlGoal,
    CrawlAgent,
    CrawlGoal,
    CrawlResult,
    KeywordCrawlGoal,
    keyword_link_score,
)
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


# ── ContactCrawlGoal (lead-gen) ───────────────────────────────────────────────


def test_keyword_link_score_prefers_keywords() -> None:
    kws = ("contact",)
    contact = Link(url="https://x.com/contact", anchor="Contact", same_domain=True)
    pricing = Link(url="https://x.com/pricing", anchor="Pricing", same_domain=True)
    assert keyword_link_score(contact, 1, kws) > keyword_link_score(pricing, 1, kws)


def test_contact_goal_finds_email_best_first_and_stops() -> None:
    agent = CrawlAgent(FakeWebScraperClient(pages=_SITE))
    result = agent.crawl("https://acme.com/", ContactCrawlGoal())
    assert isinstance(result, CrawlResult)
    assert result.findings["emails"] == ["careers@acme.com"]
    assert result.stop_reason == "goal_met"
    # Best-first: home → contact (high score); /pricing never wastes the budget.
    assert "https://acme.com/contact" in result.pages_visited
    assert "https://acme.com/pricing" not in result.pages_visited


def test_contact_goal_captures_context() -> None:
    result = CrawlAgent(FakeWebScraperClient(pages=_SITE)).crawl(
        "https://acme.com/", ContactCrawlGoal()
    )
    assert "Acme" in result.findings["context"]


def test_contact_goal_satisfies_protocol() -> None:
    assert isinstance(ContactCrawlGoal(), CrawlGoal)
    assert isinstance(KeywordCrawlGoal(["x"]), CrawlGoal)


# ── Agent mechanism (goal-agnostic) ───────────────────────────────────────────


def test_crawl_stays_on_domain() -> None:
    result = CrawlAgent(FakeWebScraperClient(pages=_SITE)).crawl(
        "https://acme.com/", ContactCrawlGoal()
    )
    assert all("acme.com" in u for u in result.pages_visited)
    assert all("twitter.com" not in u for u in result.pages_visited)


def test_crawl_respects_page_budget() -> None:
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
    result = agent.crawl("https://acme.com/", ContactCrawlGoal())
    assert result.pages_count == 2
    assert result.stop_reason == "budget_pages"


def test_crawl_dedupes_visited() -> None:
    site = {
        "https://acme.com/": _page(
            "https://acme.com/", "home", [("https://acme.com/x", "about")]
        ),
        "https://acme.com/x": _page(
            "https://acme.com/x", "x", [("https://acme.com/", "home")]
        ),
    }
    agent = CrawlAgent(FakeWebScraperClient(pages=site), max_pages=10)
    result = agent.crawl("https://acme.com/", ContactCrawlGoal())
    assert sorted(result.pages_visited) == ["https://acme.com/", "https://acme.com/x"]


def test_crawl_failure_is_non_fatal() -> None:
    class _Boom:
        def scrape(self, url: str) -> ScrapedPage:
            raise RuntimeError("network down")

    result = CrawlAgent(_Boom()).crawl("https://acme.com/", ContactCrawlGoal())
    assert result.findings["emails"] == []
    assert result.pages_count == 0


def test_agent_is_goal_agnostic_with_stub_goal() -> None:
    # A trivial goal that stops after the first page — proves the agent delegates
    # all intent to the goal and carries no lead-gen assumptions.
    class StopFirst:
        def __init__(self) -> None:
            self.seen = 0

        def score_link(self, link: Link, depth: int) -> float:
            return 1.0

        def absorb(self, page: ScrapedPage) -> None:
            self.seen += 1

        def satisfied(self) -> bool:
            return self.seen >= 1

        def result(self) -> dict[str, Any]:
            return {"seen": self.seen}

    result = CrawlAgent(FakeWebScraperClient(pages=_SITE)).crawl(
        "https://acme.com/", StopFirst()
    )
    assert result.stop_reason == "goal_met"
    assert result.findings == {"seen": 1}


# ── KeywordCrawlGoal (2nd goal — proves reuse beyond lead-gen) ────────────────


def test_keyword_goal_collects_matching_pages() -> None:
    site = {
        "https://acme.com/": _page(
            "https://acme.com/",
            "home",
            [
                ("https://acme.com/pricing", "Pricing"),
                ("https://acme.com/features", "Features"),
                ("https://acme.com/blog", "Blog"),
            ],
        ),
        "https://acme.com/pricing": _page(
            "https://acme.com/pricing", "Our pricing starts at $99/mo.", []
        ),
        "https://acme.com/features": _page(
            "https://acme.com/features", "Pricing tiers and features compared.", []
        ),
        "https://acme.com/blog": _page("https://acme.com/blog", "company blog", []),
    }
    goal = KeywordCrawlGoal(["pricing"], min_matches=2)
    result = CrawlAgent(FakeWebScraperClient(pages=site), max_pages=10).crawl(
        "https://acme.com/", goal
    )
    matched_urls = {m["url"] for m in result.findings["matches"]}
    assert "https://acme.com/pricing" in matched_urls
    assert "https://acme.com/features" in matched_urls
    assert result.stop_reason == "goal_met"
