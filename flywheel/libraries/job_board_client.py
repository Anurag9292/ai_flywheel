"""``job-board-client`` — derived in PostlineAI's outbound lead-gen step.

A **library tool** (leaf I/O) wrapping job sources. Pure function calls; no
events.

> *The venture needs to: find companies that are *actively hiring* for content,
> brand, or marketing roles — a strong "they need help with content right now"
> buying signal — and gather enough of each posting to infer what the company
> most needs.*

Two implementations live behind the ``JobBoardClient`` Protocol:

- ``FakeJobBoardClient`` — deterministic canned postings (the default; keeps
  tests, CI, demos and ``/topology`` offline).
- ``MultiATSJobBoardClient`` — **real, and free.** Fans out across a curated
  roster of companies and hits the *public, unauthenticated* job-board JSON
  APIs that Greenhouse, Lever and Ashby expose for every customer. No API key,
  no scraping, no cost. Each ATS's JSON is normalized into our ``JobPosting``,
  HTML descriptions are stripped to text, a ``contact_email`` is best-effort
  extracted from the description, and results are deduplicated via a
  ``LeadStore`` so the same role isn't surfaced twice.

Per ``new_docs/stack.md`` the real client uses ``httpx`` + ``tenacity`` (the
optional ``lead-gen`` extra). It is imported lazily so the fake path needs none
of it. Career-page enrichment (Firecrawl) is a *separate*, opt-in library
(``web-scraper-client``); discovery here is free regardless.

Convention: a ``JobPosting`` carries the **company contact email** when the
source exposes one. ``contact_email`` may be ``""`` when unknown — downstream
nodes treat empty as "no email signal".
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import structlog
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from flywheel.libraries.lead_store import LeadStore

log = structlog.get_logger("flywheel.lead_sourcer")

# Shared email matcher (same shape used by web-scraper-client). Surfaces
# ``careers@…`` / ``hiring@…`` from a job description when the ATS includes one.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Crude HTML tag stripper — ATS descriptions come as HTML; we want plain text
# for the needs-analysis prompt. Not a full parser (no bs4 dependency).
_TAG_RE = re.compile(r"<[^>]+>")


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


# ── Shared helpers (used by the fake's filter + the real ATS clients) ─────────


def matches_criteria(posting: JobPosting, criteria: JobSearchCriteria) -> bool:
    """Whether ``posting`` satisfies ``criteria`` (case-insensitive substring).

    A field with no criteria terms is not constrained. With no terms at all,
    everything matches (the caller decides whether to cap by ``limit``).
    """
    terms_kw = [k.lower() for k in criteria.keywords]
    terms_title = [t.lower() for t in criteria.titles]
    terms_loc = [loc.lower() for loc in criteria.locations]
    terms_dep = [d.lower() for d in criteria.departments]
    if not (terms_kw or terms_title or terms_loc or terms_dep):
        return True
    haystack = " ".join([posting.title, posting.description, posting.department]).lower()
    if terms_kw and not any(t in haystack for t in terms_kw):
        return False
    if terms_title and not any(t in posting.title.lower() for t in terms_title):
        return False
    if terms_loc and not any(t in posting.location.lower() for t in terms_loc):
        return False
    if terms_dep and not any(t in posting.department.lower() for t in terms_dep):
        return False
    return True


def html_to_text(raw: str) -> str:
    """Strip HTML tags + unescape entities → plain text (collapsed whitespace)."""
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return " ".join(text.split())


def first_email_in(text: str) -> str:
    """Return the first email found in ``text``, or ``""``."""
    match = _EMAIL_RE.search(text or "")
    return match.group(0) if match else ""


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
        out: list[JobPosting] = []
        for posting in self._fixtures:
            if matches_criteria(posting, criteria):
                out.append(posting)
            if len(out) >= criteria.limit:
                break
        return out


# ── Real, free ATS clients (public unauthenticated job-board JSON APIs) ───────


class CompanyRef(BaseModel):
    """One company in the curated roster: which ATS + that company's board token.

    Public ATS APIs are *per-company* — you must know the company's board token
    (the slug in its hosted job-board URL). See ``ventures/lead_sources.yaml``.
    """

    ats: str  # "greenhouse" | "lever" | "ashby"
    token: str
    # Optional human label; falls back to the token in normalized postings.
    name: str = ""


def load_roster(path: str | None = None) -> list[CompanyRef]:
    """Load the curated company roster from ``ventures/lead_sources.yaml``.

    Imports are local so the fake path never touches PyYAML/filesystem. Returns
    an empty list if the file is missing (a live run with no roster simply finds
    nothing, rather than crashing).
    """
    from pathlib import Path

    import yaml

    roster_path = (
        Path(path)
        if path
        else Path(__file__).resolve().parents[2] / "ventures" / "lead_sources.yaml"
    )
    if not roster_path.exists():
        return []
    data = yaml.safe_load(roster_path.read_text(encoding="utf-8")) or {}
    return [CompanyRef.model_validate(c) for c in data.get("companies", [])]


def normalize_greenhouse(payload: dict[str, Any], company: str) -> list[JobPosting]:
    """Map a Greenhouse Job Board API response to ``JobPosting``s.

    Endpoint: ``boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true``.
    Fields: ``jobs[].title``, ``.location.name``, ``.content`` (HTML, escaped),
    ``.absolute_url``, ``.updated_at``, optional ``.departments[].name``.
    """
    out: list[JobPosting] = []
    for job in payload.get("jobs", []) or []:
        location = (job.get("location") or {}).get("name", "") or ""
        departments = job.get("departments") or []
        department = departments[0].get("name", "") if departments else ""
        # Greenhouse double-escapes content; html_to_text unescapes once and the
        # value itself is already entity-escaped, so unescape twice via the tag
        # stripper + html.unescape inside html_to_text handles the common case.
        description = html_to_text(html.unescape(job.get("content", "") or ""))
        out.append(
            JobPosting(
                company=company,
                title=job.get("title", "") or "",
                location=location,
                department=department,
                url=job.get("absolute_url", "") or "",
                posted_at=job.get("updated_at", "") or "",
                description=description,
                contact_email=first_email_in(description),
            )
        )
    return out


def normalize_lever(payload: list[dict[str, Any]], company: str) -> list[JobPosting]:
    """Map a Lever postings API response to ``JobPosting``s.

    Endpoint: ``api.lever.co/v0/postings/{token}?mode=json`` (returns a list).
    Fields: ``text`` (title), ``categories.{location,team,commitment}``,
    ``descriptionPlain`` / ``description`` (HTML), ``hostedUrl``, ``createdAt``.
    """
    out: list[JobPosting] = []
    for job in payload or []:
        categories = job.get("categories") or {}
        description = job.get("descriptionPlain") or html_to_text(
            job.get("description", "") or ""
        )
        out.append(
            JobPosting(
                company=company,
                title=job.get("text", "") or "",
                location=categories.get("location", "") or "",
                department=categories.get("team", "") or "",
                url=job.get("hostedUrl", "") or "",
                posted_at=str(job.get("createdAt", "") or ""),
                description=description,
                contact_email=first_email_in(description),
            )
        )
    return out


def normalize_ashby(payload: dict[str, Any], company: str) -> list[JobPosting]:
    """Map an Ashby Job Posting API response to ``JobPosting``s.

    Endpoint: ``api.ashbyhq.com/posting-api/job-board/{token}``.
    Fields: ``jobs[].title``, ``.location``, ``.department``, ``.descriptionPlain``
    / ``.descriptionHtml``, ``.jobUrl``, ``.publishedAt``, ``.isRemote``.
    """
    out: list[JobPosting] = []
    for job in payload.get("jobs", []) or []:
        location = job.get("location", "") or ""
        if not location and job.get("isRemote"):
            location = "Remote"
        description = job.get("descriptionPlain") or html_to_text(
            job.get("descriptionHtml", "") or ""
        )
        out.append(
            JobPosting(
                company=company,
                title=job.get("title", "") or "",
                location=location,
                department=job.get("department", "") or "",
                url=job.get("jobUrl", "") or "",
                posted_at=job.get("publishedAt", "") or "",
                description=description,
                contact_email=first_email_in(description),
            )
        )
    return out


# Per-ATS endpoint templates + normalizer. Keyed by the ``CompanyRef.ats`` value.
_ATS_ENDPOINTS: dict[str, str] = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{token}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{token}",
}


def _normalize(ats: str, payload: Any, company: str) -> list[JobPosting]:
    if ats == "greenhouse":
        return normalize_greenhouse(payload, company)
    if ats == "lever":
        return normalize_lever(payload, company)
    if ats == "ashby":
        return normalize_ashby(payload, company)
    raise ValueError(f"Unknown ATS {ats!r}. Known: {', '.join(_ATS_ENDPOINTS)}")


class FetchError(BaseModel):
    """A per-board failure captured during a scan (for observability)."""

    ats: str = ""
    token: str = ""
    url: str = ""
    error: str = ""  # "<ExceptionType>: <message>"


class MultiATSJobBoardClient:
    """Real, free job-board client over public ATS APIs.

    Fans out across a curated ``roster`` of companies, fetches each one's public
    board, normalizes to ``JobPosting``, filters by criteria, and deduplicates by
    URL via a ``LeadStore``. Uses ``httpx`` + ``tenacity`` (the ``lead-gen``
    extra), imported lazily so the fake path doesn't require them.

    The HTTP client is injectable (``fetch_json``) purely so tests can drive it
    with canned JSON and zero network.

    **Observability:** a failing board no longer fails silently. Each fetch/parse
    failure is logged (``flywheel.lead_sourcer`` via ``structlog``) *and* recorded
    on :attr:`last_errors` from the most recent ``search_postings`` call, so the
    dev API / a debugger can show *why* a board returned nothing. Crucially, a
    missing dependency (the ``lead-gen`` extra not installed) raises a clear
    :class:`RuntimeError` instead of being swallowed as "a bad board".
    """

    def __init__(
        self,
        roster: list[CompanyRef],
        *,
        store: LeadStore | None = None,
        timeout: float = 10.0,
        fetch_json: Any | None = None,
    ) -> None:
        from flywheel.libraries.lead_store import InMemoryLeadStore

        self._roster = list(roster)
        self._store: LeadStore = store or InMemoryLeadStore()
        self._timeout = timeout
        self._fetch_json = fetch_json or self._default_fetch_json
        # Per-board failures from the most recent search (cleared on each call).
        self.last_errors: list[FetchError] = []

    def search_postings(self, criteria: JobSearchCriteria) -> list[JobPosting]:
        out: list[JobPosting] = []
        self.last_errors = []
        for ref in self._roster:
            if len(out) >= criteria.limit:
                break
            url = _ATS_ENDPOINTS.get(ref.ats, "").format(token=ref.token)
            if not url:
                log.warning(
                    "lead_sourcer.unknown_ats", ats=ref.ats, token=ref.token
                )
                self.last_errors.append(
                    FetchError(
                        ats=ref.ats,
                        token=ref.token,
                        error=f"unknown ATS {ref.ats!r}",
                    )
                )
                continue
            try:
                payload = self._fetch_json(url)
            except Exception as exc:  # noqa: BLE001
                # One bad board must not kill the whole scan — but it must be
                # VISIBLE. We log it and record it; we do NOT silently drop it.
                detail = f"{type(exc).__name__}: {exc}"
                log.warning(
                    "lead_sourcer.fetch_failed",
                    ats=ref.ats,
                    token=ref.token,
                    url=url,
                    error=detail,
                )
                self.last_errors.append(
                    FetchError(ats=ref.ats, token=ref.token, url=url, error=detail)
                )
                continue
            company = ref.name or ref.token
            for posting in _normalize(ref.ats, payload, company):
                if not matches_criteria(posting, criteria):
                    continue
                if self._store.seen(posting.url):
                    continue  # already surfaced in a previous scan
                self._store.mark_seen(posting.url)
                out.append(posting)
                if len(out) >= criteria.limit:
                    break
        log.info(
            "lead_sourcer.scan_complete",
            boards=len(self._roster),
            failed=len(self.last_errors),
            postings=len(out),
        )
        return out

    def _default_fetch_json(self, url: str) -> Any:
        """Fetch + parse JSON with retry/backoff. Imports httpx/tenacity lazily.

        A missing ``lead-gen`` extra surfaces as a clear ``RuntimeError`` (with
        the install command) rather than a swallowed ImportError — that was a
        likely cause of "every board fails" in an under-provisioned environment.
        """
        try:
            import httpx
            from tenacity import (
                retry,
                retry_if_exception_type,
                stop_after_attempt,
                wait_exponential,
            )
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "Live lead-gen needs the 'lead-gen' extra. Install it with: "
                "uv pip install -e '.[lead-gen]'  (provides httpx + tenacity)."
            ) from exc

        @retry(
            retry=retry_if_exception_type(httpx.HTTPError),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, max=4),
            reraise=True,
        )
        def _get() -> Any:
            resp = httpx.get(
                url,
                timeout=self._timeout,
                headers={"User-Agent": "ai-flywheel-leadgen/0.1 (+postlineai)"},
            )
            resp.raise_for_status()
            return resp.json()

        return _get()
