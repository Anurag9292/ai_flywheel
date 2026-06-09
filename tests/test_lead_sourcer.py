"""Tests for ``lead-sourcer``."""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.job_board_client import (
    FakeJobBoardClient,
    JobPosting,
    JobSearchCriteria,
)
from flywheel.libraries.web_scraper_client import FakeWebScraperClient, ScrapedPage
from flywheel.nodes.lead_sourcer import (
    CompaniesDiscovered,
    CompanyLead,
    LeadSourcer,
)


def _runtime(tmp_path, sourcer):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(sourcer)
    return bus, runtime


def test_lead_sourcer_emits_companies_discovered(tmp_path) -> None:
    sourcer = LeadSourcer()
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)

    bus.publish(
        Event(
            type="lead-search.requested",
            venture_id="postlineai",
            payload={"criteria": JobSearchCriteria(keywords=["linkedin"]).model_dump()},
        )
    )

    assert len(out) == 1
    payload = CompaniesDiscovered.model_validate(out[0].payload)
    assert {c.company for c in payload.companies} == {"Lumenlift", "Cobaltbase"}


def test_lead_sourcer_groups_postings_by_company(tmp_path) -> None:
    fixtures = [
        JobPosting(company="Acme", title="Head of Content", contact_email=""),
        JobPosting(company="Acme", title="Brand Lead"),
        JobPosting(company="Globex", title="Founder Brand Lead"),
    ]
    sourcer = LeadSourcer(job_board=FakeJobBoardClient(fixtures=fixtures))
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)

    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))

    payload = CompaniesDiscovered.model_validate(out[0].payload)
    by_co: dict[str, CompanyLead] = {c.company: c for c in payload.companies}
    assert sorted(by_co) == ["Acme", "Globex"]
    assert len(by_co["Acme"].postings) == 2
    assert len(by_co["Globex"].postings) == 1


def test_lead_sourcer_uses_default_criteria_when_payload_empty(tmp_path) -> None:
    # Default criteria filters to "linkedin", which Cobaltbase + Lumenlift match.
    default = JobSearchCriteria(keywords=["linkedin"])
    sourcer = LeadSourcer(default_criteria=default)
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)

    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))

    payload = CompaniesDiscovered.model_validate(out[0].payload)
    assert {c.company for c in payload.companies} == {"Lumenlift", "Cobaltbase"}


def test_lead_sourcer_enriches_email_from_career_page(tmp_path) -> None:
    # Posting has no contact email; scraper supplies one from the career page.
    fixtures = [
        JobPosting(
            company="Stark Industries",
            title="Head of Content",
            url="https://stark.example.com/careers/head-of-content",
        )
    ]
    pages = {
        "https://stark.example.com/careers/head-of-content": ScrapedPage(
            url="https://stark.example.com/careers/head-of-content",
            text="Reach the hiring manager at hiring@stark.example.com.",
        )
    }
    sourcer = LeadSourcer(
        job_board=FakeJobBoardClient(fixtures=fixtures),
        scraper=FakeWebScraperClient(pages=pages),
    )
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)

    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))
    payload = CompaniesDiscovered.model_validate(out[0].payload)
    assert payload.companies[0].contact_email == "hiring@stark.example.com"


def test_lead_sourcer_preserves_correlation_id(tmp_path) -> None:
    sourcer = LeadSourcer()
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)

    trigger = Event(type="lead-search.requested", venture_id="v", payload={})
    bus.publish(trigger)
    assert out[0].correlation_id == trigger.correlation_id


def test_lead_sourcer_surfaces_fetch_errors_in_event(tmp_path) -> None:
    # A job board that records last_errors (like the live MultiATSJobBoardClient)
    # has those errors surfaced in the emitted companies.discovered payload, so a
    # live run that found nothing explains *why* in the trace.
    from flywheel.libraries.job_board_client import FetchError

    class _FailingBoard:
        def __init__(self) -> None:
            self.last_errors: list[FetchError] = []

        def search_postings(self, criteria: JobSearchCriteria) -> list[JobPosting]:
            self.last_errors = [
                FetchError(
                    ats="lever",
                    token="globex",
                    url="https://api.lever.co/v0/postings/globex?mode=json",
                    error="ConnectError: network unreachable",
                )
            ]
            return []

    sourcer = LeadSourcer(job_board=_FailingBoard())
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)

    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))
    payload = CompaniesDiscovered.model_validate(out[0].payload)
    assert payload.companies == []
    assert len(payload.fetch_errors) == 1
    assert payload.fetch_errors[0]["ats"] == "lever"
    assert "ConnectError" in payload.fetch_errors[0]["error"]


def test_lead_sourcer_no_fetch_errors_for_fake_board(tmp_path) -> None:
    # The fake board has no last_errors → fetch_errors stays empty.
    sourcer = LeadSourcer()
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)
    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))
    payload = CompaniesDiscovered.model_validate(out[0].payload)
    assert payload.fetch_errors == []
