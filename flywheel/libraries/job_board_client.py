"""``job-board-client`` — derived in PostlineAI's outbound lead-gen step.

A **library tool** (leaf I/O) wrapping job aggregators (e.g. an Indeed / LinkedIn
Jobs / Greenhouse / Lever API, or a managed scraping provider). Pure function
calls; no events.

> *The venture needs to: find companies that are *actively hiring* for content,
> brand, or marketing roles — a strong "they need help with content right now"
> buying signal — and gather enough of each posting to infer what the company
> most needs.*

Fake-first per ``new_docs/stack.md``: the real httpx-backed impl swaps in behind
the ``JobBoardClient`` Protocol when we want live results. The fake is seeded
with a small fixture so ``lead-sourcer`` can run end-to-end without network.

Convention: a ``JobPosting`` carries the **company contact email** when the
source exposes it (some career pages and ATSs do). ``contact_email`` may be ``""``
when unknown — downstream nodes treat empty as "no email signal".
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    """One job posting surfaced from a board / aggregator / ATS.

    ``description`` is intentionally short (the snippet/summary returned by the
    board) — full page text is a separate call via ``web-scraper-client``.
    """

    company: str = ""
    title: str = ""
    location: str = ""
    department: str = ""
    url: str = ""
    posted_at: str = ""  # ISO date as a string (deferred: real datetime parsing)
    description: str = ""
    # Best-effort contact email if the source exposes one (careers@, hiring@, ...).
    contact_email: str = ""


class JobSearchCriteria(BaseModel):
    """What to look for. Carried in the ``lead-search.requested`` event payload.

    Mirrors how the ``signal-analyzer``'s rubric travels in the event payload —
    *not* node config — so the criteria can change run-to-run without rebuilding
    the runtime.
    """

    keywords: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    limit: int = 25


@runtime_checkable
class JobBoardClient(Protocol):
    def search_postings(self, criteria: JobSearchCriteria) -> list[JobPosting]: ...


class FakeJobBoardClient:
    """Offline job board returning deterministic canned postings.

    Seeded with a small fixture so ``lead-sourcer`` can run end-to-end. Matching
    is intentionally simple: a fixture posting matches when *any* of the
    criteria's keywords / titles / locations / departments substring-matches the
    corresponding posting field (case-insensitive). Unknown criteria return the
    full fixture so demos always produce something.
    """

    # A small built-in fixture, used when no fixtures are passed. Designed so
    # the canned PostlineAI lead-gen demo always finds plausible companies
    # hiring for the kind of role that signals they need content help.
    DEFAULT_FIXTURES: list[JobPosting] = [
        JobPosting(
            company="Northwind Robotics",
            title="Head of Content Marketing",
            location="Remote",
            department="Marketing",
            url="https://northwind.example.com/careers/head-of-content",
            posted_at="2025-05-20",
            description=(
                "We're looking for a senior content lead to own thought "
                "leadership and founder-led content for our B2B SaaS audience."
            ),
            contact_email="careers@northwind.example.com",
        ),
        JobPosting(
            company="Lumenlift",
            title="Content Marketing Manager",
            location="New York, NY",
            department="Marketing",
            url="https://lumenlift.example.com/jobs/cmm",
            posted_at="2025-05-18",
            description=(
                "Drive our LinkedIn presence end-to-end. Ghostwrite for the "
                "founder, run the editorial calendar, grow inbound."
            ),
            contact_email="hiring@lumenlift.example.com",
        ),
        JobPosting(
            company="Cobaltbase",
            title="Founder Brand Lead",
            location="Remote",
            department="Marketing",
            url="https://cobaltbase.example.com/roles/founder-brand",
            posted_at="2025-05-22",
            description=(
                "Help our CEO build a top-1% LinkedIn presence. You'll write "
                "in their voice and turn customer conversations into posts."
            ),
            # No contact email exposed — downstream nodes handle "" gracefully.
            contact_email="",
        ),
    ]

    def __init__(self, fixtures: list[JobPosting] | None = None) -> None:
        self._fixtures = list(fixtures) if fixtures is not None else list(self.DEFAULT_FIXTURES)

    def search_postings(self, criteria: JobSearchCriteria) -> list[JobPosting]:
        terms_kw = [k.lower() for k in criteria.keywords]
        terms_title = [t.lower() for t in criteria.titles]
        terms_loc = [loc.lower() for loc in criteria.locations]
        terms_dep = [d.lower() for d in criteria.departments]

        # No criteria at all → return the full fixture (capped by limit).
        empty = not (terms_kw or terms_title or terms_loc or terms_dep)

        out: list[JobPosting] = []
        for posting in self._fixtures:
            if empty or self._matches(posting, terms_kw, terms_title, terms_loc, terms_dep):
                out.append(posting)
            if len(out) >= criteria.limit:
                break
        return out

    @staticmethod
    def _matches(
        posting: JobPosting,
        terms_kw: list[str],
        terms_title: list[str],
        terms_loc: list[str],
        terms_dep: list[str],
    ) -> bool:
        haystack = " ".join(
            [posting.title, posting.description, posting.department]
        ).lower()
        if terms_kw and not any(t in haystack for t in terms_kw):
            return False
        if terms_title and not any(t in posting.title.lower() for t in terms_title):
            return False
        if terms_loc and not any(t in posting.location.lower() for t in terms_loc):
            return False
        if terms_dep and not any(t in posting.department.lower() for t in terms_dep):
            return False
        return True
