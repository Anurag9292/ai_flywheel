"""The node registry: maps a node *name* to a factory that builds it.

This is the single place that knows how to instantiate a Layer 1 node by the
string name used in a venture file. Factories accept a ``config`` dict (from the
venture's ``NodeSpec.config``) so per-venture construction bindings are honored
(e.g. ``post-drafter`` ``impl``).

The agentic demo nodes (``market-scanner``, ``pain-extractor``,
``signal-analyzer``) default to the **canned fake-gateway** variants that the dev
runtime has always used, so loading the venture reproduces today's deterministic
behavior exactly. Pass ``config: {canned: false}`` to get a plain node instead.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from flywheel.core.node import Node
from flywheel.libraries.job_board_client import (
    FakeJobBoardClient,
    JobSearchCriteria,
    MultiATSJobBoardClient,
    load_roster,
)
from flywheel.libraries.lead_store import InMemoryLeadStore
from flywheel.libraries.llm_gateway import FakeLLMGateway, LiteLLMGateway
from flywheel.libraries.semrush_client import FakeSemrushClient, KeywordVolume
from flywheel.libraries.web_scraper_client import (
    FakeWebScraperClient,
    FirecrawlScraperClient,
    WebScraperClient,
)
from flywheel.libraries.web_search_client import FakeWebSearchClient, SearchResult
from flywheel.nodes.ad_analytics_collector import AdAnalyticsCollector
from flywheel.nodes.ad_campaign_runner import AdCampaignRunner
from flywheel.nodes.company_needs_analyzer import (
    CompanyNeedsAnalyzer,
    CompanyNeedsReport,
)
from flywheel.nodes.customer_survey import CustomerSurvey
from flywheel.nodes.founder_notifier import FounderNotifier
from flywheel.nodes.human_review_queue import DEFAULT_RESULT_MAP, HumanReviewQueue
from flywheel.nodes.input_intake import InputIntake
from flywheel.nodes.lead_sourcer import LeadSourcer
from flywheel.nodes.market_scanner import MarketMap, MarketScanner
from flywheel.nodes.pain_extractor import PainExtractor, PainReport
from flywheel.nodes.pitch_generator import Pitch, PitchGenerator
from flywheel.nodes.post_analytics_collector import PostAnalyticsCollector
from flywheel.nodes.post_drafter import HumanDrafter, PostDrafter
from flywheel.nodes.post_scheduler import PostScheduler
from flywheel.nodes.signal_analyzer import SignalAnalyzer, SignalVerdict
from flywheel.nodes.subscription_manager import SubscriptionManager
from flywheel.nodes.thesis_tracker import ThesisTracker

NodeFactory = Callable[[dict[str, Any]], Node]


# ── Canned agentic demo nodes (reproduce the dev runtime's deterministic output) ──


def _market_scanner(config: dict[str, Any]) -> Node:
    if not config.get("canned", True):
        return MarketScanner()
    gateway = FakeLLMGateway()
    gateway.register(
        MarketMap.__name__,
        lambda prompt: {
            "summary": "Crowded at the cheap end (Taplio ~$39) and premium end "
            "($5k agencies); a clear gap exists at $499 for AI-with-human-touch.",
            "competitors": [
                {"name": "Taplio", "url": "https://taplio.com", "pricing": "$39/mo",
                 "positioning": "self-serve AI tool"},
                {"name": "Agencies", "pricing": "$5k/mo", "positioning": "human DFY"},
            ],
            "top_keywords": ["linkedin ghostwriter", "b2b founder content"],
        },
    )
    return MarketScanner(
        semrush=FakeSemrushClient(
            fixtures={
                "linkedin ghostwriter": KeywordVolume(
                    keyword="linkedin ghostwriter", monthly_volume=12000, competition=0.6
                )
            }
        ),
        web_search=FakeWebSearchClient(
            results={
                "AI LinkedIn ghostwriting competitors": [
                    SearchResult(title="Taplio", url="https://taplio.com",
                                 snippet="AI LinkedIn tool, ~$39/mo."),
                ]
            }
        ),
        gateway=gateway,
    )


def _pain_extractor(config: dict[str, Any]) -> Node:
    if not config.get("canned", True):
        return PainExtractor()
    gateway = FakeLLMGateway()
    gateway.register(
        PainReport.__name__,
        lambda prompt: {
            "pains": [
                {"pain": "no time to write posts", "frequency": 8, "intensity": 0.8},
                {"pain": "posts get no engagement", "frequency": 5, "intensity": 0.7},
                {"pain": "don't know what to say", "frequency": 4, "intensity": 0.6},
            ]
        },
    )
    return PainExtractor(gateway=gateway)


def _signal_analyzer(config: dict[str, Any]) -> Node:
    if not config.get("canned", True):
        return SignalAnalyzer()
    gateway = FakeLLMGateway()
    gateway.register(
        SignalVerdict.__name__,
        lambda prompt: {
            "verdict": "strong",
            "confidence": 0.82,
            "explanation": "CPL well under target and signups above the bar for $499/mo.",
        },
    )
    return SignalAnalyzer(gateway=gateway)


def _post_drafter(config: dict[str, Any]) -> Node:
    # The Step-7 impl swap is a one-line venture-config change. Only "human" is
    # implemented today; an "agent-v1" binding arrives in Step 7.
    impl = config.get("impl", "human")
    if impl == "human":
        return PostDrafter(drafter=HumanDrafter())
    raise ValueError(f"post-drafter impl {impl!r} not implemented yet (Step 7).")


# ── Outbound lead-gen ─────────────────────────────────────────────────────────


def _require_env(var: str, node: str, purpose: str) -> str:
    """Return env var ``var`` or raise a clear error naming the node + fix.

    Used by the LIVE venture: live nodes call real backends and **fail loud** on
    a missing key rather than silently falling back to fakes (the chosen
    "if live, always real" semantics). The default offline venture never hits
    this — it builds the canned/fake variants.
    """
    value = os.environ.get(var)
    if not value:
        raise RuntimeError(
            f"Live node {node!r} needs {var} ({purpose}). Set it, or run the "
            f"default offline venture (FLYWHEEL_VENTURE=postlineai)."
        )
    return value


def _lead_sourcer(config: dict[str, Any]) -> Node:
    if not config.get("canned", True):
        return LeadSourcer()
    # The default criteria is set here so a bare ``lead-search.requested``
    # produces sensible results in the dev demo. A payload-supplied criteria
    # always wins (see ``LeadSourcer._criteria_from``). These keywords are the
    # PostlineAI ICP for outbound — companies hiring for content / brand /
    # founder-comms roles.
    default_criteria = JobSearchCriteria(
        keywords=["content", "brand", "founder", "linkedin", "thought leadership"],
        departments=["Marketing"],
        limit=10,
    )
    # ICP + offer seed the company-needs prompt downstream (carried in the
    # companies.discovered payload). From the venture domain in a fuller wiring;
    # sensible PostlineAI defaults here.
    icp = config.get("icp", "seed/Series-A B2B SaaS founders, 50-500 employees")
    offer = config.get("offer", "$499/mo done-for-you LinkedIn ghostwriting for founders")

    # ── Live mode: real discovery via public ATS APIs + REAL Firecrawl ───────
    # `config: {live: true}` scans the curated roster (ventures/lead_sources.yaml)
    # over the public Greenhouse/Lever/Ashby JSON APIs (free, no key). Per the
    # "if live, always real" rule, career-page enrichment uses Firecrawl and
    # **requires** FIRECRAWL_API_KEY — no fake fallback. The default
    # (canned/offline) path is unchanged, so tests + /topology stay deterministic.
    if config.get("live", False):
        api_key = _require_env(
            "FIRECRAWL_API_KEY", "lead-sourcer", "career-page enrichment"
        )
        scraper: WebScraperClient = FirecrawlScraperClient(api_key=api_key)
        return LeadSourcer(
            job_board=MultiATSJobBoardClient(load_roster(), store=InMemoryLeadStore()),
            scraper=scraper,
            default_criteria=default_criteria,
            icp=icp,
            offer=offer,
        )

    return LeadSourcer(
        job_board=FakeJobBoardClient(),
        scraper=FakeWebScraperClient(),
        default_criteria=default_criteria,
        icp=icp,
        offer=offer,
    )


def _company_needs_analyzer(config: dict[str, Any]) -> Node:
    if config.get("live", False):
        # Real reasoning over the real discovered companies. Requires a provider
        # key (OPENAI_API_KEY); fail loud if absent.
        _require_env("OPENAI_API_KEY", "company-needs-analyzer", "live reasoning")
        return CompanyNeedsAnalyzer(gateway=LiteLLMGateway())
    if not config.get("canned", True):
        return CompanyNeedsAnalyzer()
    gateway = FakeLLMGateway()
    gateway.register(
        CompanyNeedsReport.__name__,
        lambda prompt: {
            "companies": [
                {
                    "company": "Northwind Robotics",
                    "top_need": "founder-led thought leadership at scale",
                    "buying_signals": [
                        "hiring Head of Content Marketing",
                        "remote role; signals investment in distributed team",
                    ],
                    "fit_score": 0.86,
                    "pitch_angle": (
                        "Hiring a Head of Content is slow; we ghostwrite the "
                        "founder's LinkedIn from week one."
                    ),
                    "contact_email": "careers@northwind.example.com",
                },
                {
                    "company": "Lumenlift",
                    "top_need": "consistent founder LinkedIn posting + inbound",
                    "buying_signals": [
                        "explicitly hiring for LinkedIn ghostwriting + editorial calendar",
                    ],
                    "fit_score": 0.92,
                    "pitch_angle": (
                        "You're hiring exactly what we already do — let us run "
                        "the founder's feed while the search continues."
                    ),
                    "contact_email": "hiring@lumenlift.example.com",
                },
                {
                    "company": "Cobaltbase",
                    "top_need": "build the CEO's voice on LinkedIn from scratch",
                    "buying_signals": [
                        "Founder Brand Lead role; voice + customer-conversation focus",
                    ],
                    "fit_score": 0.78,
                    "pitch_angle": (
                        "We build a founder voice from 10 minutes of voice notes "
                        "a week — same outcome, no hire."
                    ),
                    "contact_email": "",
                },
            ]
        },
    )
    return CompanyNeedsAnalyzer(gateway=gateway)


def _pitch_generator(config: dict[str, Any]) -> Node:
    if config.get("live", False):
        # Real, tailored pitches for the real companies. Requires OPENAI_API_KEY.
        _require_env("OPENAI_API_KEY", "pitch-generator", "live pitch drafting")
        return PitchGenerator(gateway=LiteLLMGateway())
    if not config.get("canned", True):
        return PitchGenerator()
    gateway = FakeLLMGateway()

    def _build(prompt: str) -> dict[str, Any]:
        # Deterministic per-company canned pitch derived from the prompt — we
        # parse the company name out of the prompt template so the same canned
        # gateway works for every company in the run. Mirrors how the other
        # canned agentic nodes work (one builder per schema).
        company = ""
        for line in prompt.splitlines():
            if line.startswith("Company: "):
                company = line[len("Company: ") :].strip()
                break
        contact_email = ""
        for line in prompt.splitlines():
            if line.startswith("Contact email (use as-is): "):
                contact_email = line[len("Contact email (use as-is): ") :].strip()
                break
        angle = (
            f"Saw you're hiring for content at {company} — we can ghostwrite "
            "the founder's LinkedIn from week one."
        )
        return {
            "company": company,
            "contact_email": contact_email,
            "angle": angle,
            "email_subject": f"Ghostwriting the founder's LinkedIn at {company}",
            "email_body": (
                f"Hi {company} team,\n\n{angle}\n\nWe turn ~10 minutes of voice "
                "notes a week into a consistent, on-brand LinkedIn presence for "
                "B2B founders. Worth a 15-minute call?\n\nBest,\nPostlineAI"
            ),
            "linkedin_message": (
                f"{angle} 10 min of voice notes/week → on-brand founder posts. "
                "Open to a quick chat?"
            ),
        }

    gateway.register(Pitch.__name__, _build)
    return PitchGenerator(gateway=gateway)


# ── The human-review-queue, extended for pitch.drafted ────────────────────────


# The queue's default mapping is post.drafted -> post.approved (Step 5). The
# outbound lead-gen step adds pitch.drafted -> pitch.approved so the *same*
# review surface parks both kinds of human-gated artifact, keeping the founder
# in one inbox. This is registry-time wiring only — the queue's ``handle()``
# already supports an injected ``result_map`` (no node-code change).
_REVIEW_RESULT_MAP: dict[str, str] = {
    **DEFAULT_RESULT_MAP,
    "pitch.drafted": "pitch.approved",
}


def _human_review_queue(_config: dict[str, Any]) -> Node:
    return HumanReviewQueue(result_map=_REVIEW_RESULT_MAP)


# ── The registry ──────────────────────────────────────────────────────────────

NODE_BUILDERS: dict[str, NodeFactory] = {
    "market-scanner": _market_scanner,
    "thesis-tracker": lambda _c: ThesisTracker(),
    "pain-extractor": _pain_extractor,
    "ad-campaign-runner": lambda _c: AdCampaignRunner(),
    "ad-analytics-collector": lambda _c: AdAnalyticsCollector(),
    "signal-analyzer": _signal_analyzer,
    "founder-notifier": lambda _c: FounderNotifier(),
    "input-intake": lambda _c: InputIntake(),
    "post-drafter": _post_drafter,
    "human-review-queue": _human_review_queue,
    "post-scheduler": lambda _c: PostScheduler(),
    "subscription-manager": lambda _c: SubscriptionManager(),
    "post-analytics-collector": lambda _c: PostAnalyticsCollector(),
    "customer-survey": lambda _c: CustomerSurvey(),
    # Outbound lead-gen (PostlineAI customer acquisition).
    "lead-sourcer": _lead_sourcer,
    "company-needs-analyzer": _company_needs_analyzer,
    "pitch-generator": _pitch_generator,
}


def known_node_names() -> list[str]:
    return sorted(NODE_BUILDERS)


def build_node(name: str, config: dict[str, Any] | None = None) -> Node:
    """Instantiate a node by registry name with optional construction config."""
    factory = NODE_BUILDERS.get(name)
    if factory is None:
        raise KeyError(f"Unknown node {name!r}. Known: {', '.join(known_node_names())}")
    return factory(config or {})
