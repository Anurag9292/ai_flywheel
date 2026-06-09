"""Tests for the real, free ATS job-board clients (no network).

Each ATS normalizer is tested against a canned JSON fixture shaped like the
real public API responses (Greenhouse / Lever / Ashby). The MultiATS client is
driven via an injected ``fetch_json`` so the whole fan-out runs offline.
"""

from __future__ import annotations

from typing import Any

from flywheel.libraries.job_board_client import (
    CompanyRef,
    JobSearchCriteria,
    MultiATSJobBoardClient,
    first_email_in,
    html_to_text,
    normalize_ashby,
    normalize_greenhouse,
    normalize_lever,
)
from flywheel.libraries.lead_store import InMemoryLeadStore

# ── helpers ───────────────────────────────────────────────────────────────────


def test_html_to_text_strips_tags_and_unescapes() -> None:
    assert html_to_text("<p>Hello&amp;&nbsp;world</p>") == "Hello& world"
    assert html_to_text("") == ""


def test_first_email_in() -> None:
    assert first_email_in("ping careers@acme.com please") == "careers@acme.com"
    assert first_email_in("no email here") == ""


# ── Greenhouse ──────────────────────────────────────────────────────────────


GREENHOUSE_FIXTURE: dict[str, Any] = {
    "jobs": [
        {
            "title": "Head of Content Marketing",
            "location": {"name": "Remote"},
            "departments": [{"name": "Marketing"}],
            "content": "&lt;p&gt;Own founder content. Email careers@acme.com&lt;/p&gt;",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            "updated_at": "2025-05-20T10:00:00Z",
        }
    ],
    "meta": {"total": 1},
}


def test_normalize_greenhouse() -> None:
    out = normalize_greenhouse(GREENHOUSE_FIXTURE, "Acme")
    assert len(out) == 1
    job = out[0]
    assert job.company == "Acme"
    assert job.title == "Head of Content Marketing"
    assert job.location == "Remote"
    assert job.department == "Marketing"
    assert job.url == "https://boards.greenhouse.io/acme/jobs/1"
    assert "Own founder content" in job.description
    assert "<p>" not in job.description  # HTML stripped
    assert job.contact_email == "careers@acme.com"


# ── Lever ─────────────────────────────────────────────────────────────────────


LEVER_FIXTURE: list[dict[str, Any]] = [
    {
        "text": "Content Marketing Manager",
        "categories": {"location": "New York, NY", "team": "Marketing"},
        "descriptionPlain": "Run LinkedIn. Reach us at hiring@globex.com.",
        "hostedUrl": "https://jobs.lever.co/globex/abc",
        "createdAt": 1716000000000,
    }
]


def test_normalize_lever() -> None:
    out = normalize_lever(LEVER_FIXTURE, "Globex")
    assert len(out) == 1
    job = out[0]
    assert job.title == "Content Marketing Manager"
    assert job.location == "New York, NY"
    assert job.department == "Marketing"
    assert job.url == "https://jobs.lever.co/globex/abc"
    assert job.contact_email == "hiring@globex.com"


# ── Ashby ─────────────────────────────────────────────────────────────────────


ASHBY_FIXTURE: dict[str, Any] = {
    "jobs": [
        {
            "title": "Founder Brand Lead",
            "location": "",
            "isRemote": True,
            "department": "Marketing",
            "descriptionPlain": "Build the CEO voice on LinkedIn.",
            "jobUrl": "https://jobs.ashbyhq.com/initech/xyz",
            "publishedAt": "2025-05-22T00:00:00Z",
        }
    ]
}


def test_normalize_ashby_uses_remote_when_no_location() -> None:
    out = normalize_ashby(ASHBY_FIXTURE, "Initech")
    assert len(out) == 1
    job = out[0]
    assert job.title == "Founder Brand Lead"
    assert job.location == "Remote"  # derived from isRemote
    assert job.url == "https://jobs.ashbyhq.com/initech/xyz"


# ── MultiATSJobBoardClient (offline via injected fetch_json) ──────────────────


def _fake_fetch(url: str) -> Any:
    if "greenhouse" in url:
        return GREENHOUSE_FIXTURE
    if "lever" in url:
        return LEVER_FIXTURE
    if "ashby" in url:
        return ASHBY_FIXTURE
    raise AssertionError(f"unexpected url {url}")


def _client(store: InMemoryLeadStore | None = None) -> MultiATSJobBoardClient:
    roster = [
        CompanyRef(ats="greenhouse", token="acme", name="Acme"),
        CompanyRef(ats="lever", token="globex", name="Globex"),
        CompanyRef(ats="ashby", token="initech", name="Initech"),
    ]
    return MultiATSJobBoardClient(roster, store=store, fetch_json=_fake_fetch)


def test_multi_ats_fans_out_across_roster() -> None:
    out = _client().search_postings(JobSearchCriteria())
    assert {p.company for p in out} == {"Acme", "Globex", "Initech"}


def test_multi_ats_filters_by_criteria() -> None:
    out = _client().search_postings(JobSearchCriteria(titles=["founder brand"]))
    assert [p.company for p in out] == ["Initech"]


def test_multi_ats_dedups_via_store() -> None:
    store = InMemoryLeadStore()
    client = _client(store)
    first = client.search_postings(JobSearchCriteria())
    assert len(first) == 3
    # Second scan: every URL already seen → nothing new surfaces.
    second = client.search_postings(JobSearchCriteria())
    assert second == []


def test_multi_ats_respects_limit() -> None:
    out = _client().search_postings(JobSearchCriteria(limit=1))
    assert len(out) == 1


def test_multi_ats_skips_failing_board() -> None:
    def flaky_fetch(url: str) -> Any:
        if "lever" in url:
            raise RuntimeError("boom")
        return _fake_fetch(url)

    roster = [
        CompanyRef(ats="lever", token="globex", name="Globex"),
        CompanyRef(ats="greenhouse", token="acme", name="Acme"),
    ]
    client = MultiATSJobBoardClient(roster, fetch_json=flaky_fetch)
    out = client.search_postings(JobSearchCriteria())
    # Lever blew up but the run continued and still returned Acme.
    assert [p.company for p in out] == ["Acme"]
