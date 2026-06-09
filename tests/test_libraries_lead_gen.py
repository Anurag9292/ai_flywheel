"""Tests for the outbound lead-gen leaf libraries (Protocol + Fake)."""

from __future__ import annotations

from flywheel.libraries.job_board_client import (
    FakeJobBoardClient,
    JobBoardClient,
    JobPosting,
    JobSearchCriteria,
)
from flywheel.libraries.web_scraper_client import (
    FakeWebScraperClient,
    ScrapedPage,
    WebScraperClient,
)

# ── job-board-client ──────────────────────────────────────────────────────────


def test_job_board_default_fixtures_returned_when_no_criteria() -> None:
    client = FakeJobBoardClient()
    out = client.search_postings(JobSearchCriteria())
    assert len(out) == len(FakeJobBoardClient.DEFAULT_FIXTURES)
    assert {p.company for p in out} == {"Northwind Robotics", "Lumenlift", "Cobaltbase"}


def test_job_board_filters_by_keyword_substring() -> None:
    client = FakeJobBoardClient()
    out = client.search_postings(JobSearchCriteria(keywords=["linkedin"]))
    # Only the postings whose title/description mentions linkedin should match.
    assert {p.company for p in out} == {"Lumenlift", "Cobaltbase"}


def test_job_board_filters_by_title_and_location() -> None:
    client = FakeJobBoardClient()
    out = client.search_postings(
        JobSearchCriteria(titles=["content marketing"], locations=["new york"])
    )
    assert len(out) == 1
    assert out[0].company == "Lumenlift"


def test_job_board_respects_limit() -> None:
    client = FakeJobBoardClient()
    out = client.search_postings(JobSearchCriteria(limit=1))
    assert len(out) == 1


def test_job_board_protocol_satisfied() -> None:
    assert isinstance(FakeJobBoardClient(), JobBoardClient)


def test_job_board_custom_fixtures_replace_defaults() -> None:
    posting = JobPosting(company="Acme", title="Editor")
    client = FakeJobBoardClient(fixtures=[posting])
    out = client.search_postings(JobSearchCriteria())
    assert out == [posting]


# ── web-scraper-client ────────────────────────────────────────────────────────


def test_scraper_returns_canned_page_for_unknown_url() -> None:
    client = FakeWebScraperClient()
    page = client.scrape("https://example.com/jobs")
    assert page.url == "https://example.com/jobs"
    assert "example.com/jobs" in page.text


def test_scraper_extracts_emails_from_canned_text() -> None:
    client = FakeWebScraperClient(
        pages={
            "https://acme.example.com/careers": ScrapedPage(
                url="https://acme.example.com/careers",
                text="Get in touch at hiring@acme.example.com or careers@acme.example.com.",
            )
        }
    )
    page = client.scrape("https://acme.example.com/careers")
    assert page.emails == [
        "hiring@acme.example.com",
        "careers@acme.example.com",
    ]


def test_scraper_preserves_pre_supplied_emails() -> None:
    client = FakeWebScraperClient(
        pages={
            "https://acme.example.com/careers": ScrapedPage(
                url="https://acme.example.com/careers",
                text="Contact us.",
                emails=["pre@acme.example.com"],
            )
        }
    )
    page = client.scrape("https://acme.example.com/careers")
    assert page.emails == ["pre@acme.example.com"]


def test_scraper_protocol_satisfied() -> None:
    assert isinstance(FakeWebScraperClient(), WebScraperClient)
