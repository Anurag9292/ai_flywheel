"""``lead-sourcer`` — derived in PostlineAI's outbound lead-gen step.

> *The venture needs to: find companies that are hiring for content / brand /
> marketing roles (a strong "they need ghostwriting" buying signal) and gather
> enough about each one to infer what they most need.*

An **event-driven node** (dumb, deterministic stitching) that reacts to
``lead-search.requested``, calls the ``job-board-client`` to fetch postings
matching the criteria, optionally enriches each company with a career-page
scrape via ``web-scraper-client`` (to surface a contact email when the board
didn't expose one), and emits one ``companies.discovered`` event carrying the
batch.

- **Reacts to:** ``lead-search.requested``.
- **Calls:** ``job-board-client``, ``web-scraper-client``.
- **Emits:** ``companies.discovered``.
- **Kind:** dumb.

The criteria can be carried in the event payload (``criteria`` block, parsed as
a :class:`JobSearchCriteria`) or, when missing, derived from the venture's
``domain`` / ICP — the dev runtime seeds them via the registry's canned config
so the demo "just works" off a single button-press.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, Field

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.job_board_client import (
    FakeJobBoardClient,
    JobBoardClient,
    JobPosting,
    JobSearchCriteria,
)
from flywheel.libraries.web_scraper_client import (
    FakeWebScraperClient,
    WebScraperClient,
)

log = structlog.get_logger("flywheel.lead_sourcer")


class CompanyLead(BaseModel):
    """One company surfaced as a lead, with the postings + signals we found."""

    company: str = ""
    postings: list[JobPosting] = Field(default_factory=list)
    # The first plausible contact email we found across postings or the career
    # page scrape. Empty when none was discoverable.
    contact_email: str = ""
    # The career-page URL we scraped (if any) and a short text snippet from it,
    # so the downstream agentic node has substrate to reason over.
    career_page_url: str = ""
    career_page_snippet: str = ""


class CompaniesDiscovered(BaseModel):
    """The structured payload for ``companies.discovered``."""

    criteria: JobSearchCriteria = Field(default_factory=JobSearchCriteria)
    companies: list[CompanyLead] = Field(default_factory=list)
    # Venture positioning carried forward so the (downstream) agentic
    # company-needs-analyzer prompt has ICP + offer context. Rubric-in-payload
    # pattern — keeps the analyzer node venture-agnostic.
    icp: str = ""
    offer: str = ""
    # Per-board failures from a live scan (empty for the fake board). Surfaced so
    # the /topology trace shows *why* a live run found nothing, instead of an
    # opaque empty result. Each item: {ats, token, url, error}.
    fetch_errors: list[dict[str, Any]] = Field(default_factory=list)


class LeadSourcer:
    name = "lead-sourcer"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["lead-search.requested"]
    emits = ["companies.discovered"]
    calls = ["job-board-client", "web-scraper-client"]

    def __init__(
        self,
        *,
        job_board: JobBoardClient | None = None,
        scraper: WebScraperClient | None = None,
        default_criteria: JobSearchCriteria | None = None,
        icp: str = "",
        offer: str = "",
        snippet_chars: int = 280,
    ) -> None:
        self._job_board = job_board or FakeJobBoardClient()
        self._scraper = scraper or FakeWebScraperClient()
        self._default_criteria = default_criteria or JobSearchCriteria()
        self._icp = icp
        self._offer = offer
        self._snippet_chars = snippet_chars

    def handle(self, event: Event, ctx: NodeContext) -> None:
        criteria = self._criteria_from(event.payload)
        postings = self._job_board.search_postings(criteria)
        companies = self._group_into_leads(postings)
        # Surface any per-board fetch failures the job board recorded (live
        # MultiATSJobBoardClient exposes `last_errors`; the fake has none). This
        # makes a live run's failures visible in the emitted event / trace.
        fetch_errors = [
            e.model_dump() if hasattr(e, "model_dump") else dict(e)
            for e in getattr(self._job_board, "last_errors", [])
        ]
        ctx.emit(
            type="companies.discovered",
            payload=CompaniesDiscovered(
                criteria=criteria,
                companies=companies,
                icp=self._icp,
                offer=self._offer,
                fetch_errors=fetch_errors,
            ).model_dump(),
        )

    # ── helpers ────────────────────────────────────────────────────────────

    def _criteria_from(self, payload: dict[str, Any]) -> JobSearchCriteria:
        """Pull the criteria from the event, falling back to the node default.

        The default is set by the registry from the venture's ICP (so a bare
        ``lead-search.requested`` produces sensible results in the dev demo)
        but a payload-supplied criteria *always* wins.
        """
        raw = payload.get("criteria")
        if raw:
            return JobSearchCriteria.model_validate(raw)
        return self._default_criteria

    def _group_into_leads(self, postings: list[JobPosting]) -> list[CompanyLead]:
        """One :class:`CompanyLead` per company, preserving discovery order.

        Dedupes postings by company; enriches each company with a career-page
        scrape *only when* no posting already supplied a contact email — this
        keeps fake-and-real impls cheap and avoids a second I/O round-trip we
        don't need.
        """
        by_company: dict[str, CompanyLead] = {}
        for posting in postings:
            lead = by_company.get(posting.company)
            if lead is None:
                lead = CompanyLead(company=posting.company)
                by_company[posting.company] = lead
            lead.postings.append(posting)
            if not lead.contact_email and posting.contact_email:
                lead.contact_email = posting.contact_email

        for lead in by_company.values():
            self._maybe_enrich_from_career_page(lead)

        return list(by_company.values())

    def _maybe_enrich_from_career_page(self, lead: CompanyLead) -> None:
        """If we still lack an email, scrape the first posting URL for one.

        **Enrichment is best-effort and never fatal.** A scraper failure (e.g. a
        bad/expired Firecrawl key, a 404, a timeout) is logged and skipped — the
        lead already has its ATS postings, and the career-page email is only a
        bonus. One failing enrichment must not blow up the whole run (mirrors the
        "one bad board must not kill the run" rule in the job-board client).
        """
        if not lead.postings:
            return
        first_url = lead.postings[0].url
        if not first_url:
            return
        # Cheap: only scrape when we still need an email *or* a snippet.
        if lead.contact_email and lead.career_page_snippet:
            return
        try:
            page = self._scraper.scrape(first_url)
        except Exception as exc:  # noqa: BLE001 — enrichment is best-effort
            log.warning(
                "lead_sourcer.enrich_failed",
                company=lead.company,
                url=first_url,
                error=f"{type(exc).__name__}: {exc}",
            )
            return
        lead.career_page_url = page.url
        if not lead.career_page_snippet:
            lead.career_page_snippet = page.text[: self._snippet_chars]
        if not lead.contact_email and page.emails:
            lead.contact_email = page.emails[0]
