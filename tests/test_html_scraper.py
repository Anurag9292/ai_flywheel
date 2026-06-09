"""Tests for HTML parsing + ScrapedPage.links (the in-house executor's core)."""

from __future__ import annotations

from flywheel.libraries.web_scraper_client import (
    FakeWebScraperClient,
    Link,
    ScrapedPage,
    parse_html,
)

_HTML = """
<html><head><title>  About Acme  </title></head>
<body>
  <nav><a href="/">Home</a> <a href="/about">About us</a></nav>
  <script>var x = "ignore@this.com";</script>
  <p>We help founders. Reach us at careers@acme.com.</p>
  <a href="https://acme.com/contact">Contact</a>
  <a href="https://twitter.com/acme">Twitter</a>
  <a href="mailto:hi@acme.com">email</a>
  <a href="#section">anchor</a>
</body></html>
"""


def test_parse_html_extracts_title_text_emails() -> None:
    page = parse_html(_HTML, "https://acme.com/")
    assert page.title == "About Acme"
    assert "We help founders" in page.text
    # script content is skipped → ignore@this.com not in text/emails
    assert "ignore@this.com" not in page.emails
    assert page.emails == ["careers@acme.com"]


def test_parse_html_extracts_links_and_tags_same_domain() -> None:
    page = parse_html(_HTML, "https://acme.com/")
    by_url = {ln.url: ln for ln in page.links}
    # relative resolved to absolute
    assert "https://acme.com/about" in by_url
    assert by_url["https://acme.com/about"].anchor == "About us"
    assert by_url["https://acme.com/about"].same_domain is True
    # external tagged off-domain
    assert by_url["https://twitter.com/acme"].same_domain is False
    # mailto / # / javascript links are dropped
    assert all(not ln.url.startswith("mailto:") for ln in page.links)
    assert all("#section" not in ln.url for ln in page.links)


def test_parse_html_handles_malformed_without_crashing() -> None:
    page = parse_html("<html><body><a href=", "https://x.com/")
    assert isinstance(page, ScrapedPage)


def test_fake_scraper_accepts_raw_html_fixture() -> None:
    fake = FakeWebScraperClient(pages={"https://acme.com/": _HTML})
    page = fake.scrape("https://acme.com/")
    assert page.emails == ["careers@acme.com"]
    assert any(ln.url == "https://acme.com/about" for ln in page.links)


def test_fake_scraper_accepts_scrapedpage_fixture() -> None:
    canned = ScrapedPage(
        url="https://acme.com/x",
        text="ping ops@acme.com",
        links=[Link(url="https://acme.com/y", anchor="y", same_domain=True)],
    )
    fake = FakeWebScraperClient(pages={"https://acme.com/x": canned})
    page = fake.scrape("https://acme.com/x")
    assert page.emails == ["ops@acme.com"]
    assert page.links[0].url == "https://acme.com/y"
