"""lead-sourcer + CrawlAgent integration: derive company domain, crawl it."""

from __future__ import annotations

from flywheel.agents.crawl_agent import CrawlAgent
from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.job_board_client import FakeJobBoardClient, JobPosting
from flywheel.libraries.web_scraper_client import FakeWebScraperClient
from flywheel.nodes.lead_sourcer import CompaniesDiscovered, CompanyLead, LeadSourcer


def _runtime(tmp_path, sourcer):
    bus = InMemoryEventBus()
    rt = Runtime(bus, TraceRecorder(bus, log_path=tmp_path / "t.jsonl"))
    rt.register(sourcer)
    return bus, rt


def test_lead_sourcer_derives_company_domain_and_crawls(tmp_path) -> None:
    # A posting hosted on Lever, whose description mentions the company's own
    # site. The crawler should seed acme.com (NOT jobs.lever.co) and find the
    # email on the contact page.
    posting = JobPosting(
        company="Acme",
        title="Head of Content",
        url="https://jobs.lever.co/acme/123",
        description="Acme is a B2B SaaS company. Learn more at https://acme.com/.",
        contact_email="",
    )
    site = {
        "https://acme.com/": "<a href='https://acme.com/contact'>Contact</a>",
        "https://acme.com/contact": "<p>Reach hiring@acme.com</p>",
    }
    crawler = CrawlAgent(FakeWebScraperClient(pages=site))
    sourcer = LeadSourcer(
        job_board=FakeJobBoardClient(fixtures=[posting]),
        crawler=crawler,
    )
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)

    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))

    payload = CompaniesDiscovered.model_validate(out[0].payload)
    lead = payload.companies[0]
    assert lead.company == "Acme"
    # Crawl seeded the company domain, not the ATS posting URL.
    assert lead.career_page_url == "https://acme.com/"
    assert lead.contact_email == "hiring@acme.com"


def test_company_seed_url_skips_ats_and_social() -> None:
    lead = CompanyLead(
        company="Globex",
        postings=[
            JobPosting(
                company="Globex",
                description=(
                    "Apply at https://jobs.lever.co/globex and follow "
                    "https://linkedin.com/company/globex — homepage https://globex.io/careers"
                ),
            )
        ],
    )
    # Should pick globex.io (skipping lever.co + linkedin.com).
    assert LeadSourcer._company_seed_url(lead) == "https://globex.io/"


def test_company_seed_url_empty_when_no_company_url() -> None:
    lead = CompanyLead(
        company="NoSite",
        postings=[JobPosting(company="NoSite", description="No links here at all.")],
    )
    assert LeadSourcer._company_seed_url(lead) == ""


def test_lead_sourcer_without_crawler_uses_single_scrape(tmp_path) -> None:
    # Backward-compat: no crawler → single-page scrape of the posting URL (the
    # fake/default path), still best-effort.
    posting = JobPosting(
        company="Acme",
        title="Head of Content",
        url="https://acme.example.com/careers/1",
        contact_email="",
    )
    pages = {"https://acme.example.com/careers/1": "<p>ping careers@acme.example.com</p>"}
    sourcer = LeadSourcer(
        job_board=FakeJobBoardClient(fixtures=[posting]),
        scraper=FakeWebScraperClient(pages=pages),
    )
    bus, _ = _runtime(tmp_path, sourcer)
    out: list[Event] = []
    bus.subscribe("companies.discovered", out.append)
    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))
    payload = CompaniesDiscovered.model_validate(out[0].payload)
    assert payload.companies[0].contact_email == "careers@acme.example.com"
