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

from flywheel.agents.crawl_agent import CrawlAgent
from flywheel.core.inferencer import FakeInferencer, LLMInferencer
from flywheel.core.node import Node
from flywheel.libraries.api_fetch_client import FakeApiFetchClient, HttpxApiFetchClient
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
    HttpxScraperClient,
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
from flywheel.nodes.insight_inferrer import InsightInferrer, InsightSet
from flywheel.nodes.knowledge_builder import KnowledgeBuilder
from flywheel.nodes.lead_sourcer import LeadSourcer
from flywheel.nodes.market_scanner import MarketMap, MarketScanner
from flywheel.nodes.pain_extractor import PainExtractor, PainReport
from flywheel.nodes.pitch_generator import Pitch, PitchGenerator
from flywheel.nodes.post_analytics_collector import PostAnalyticsCollector
from flywheel.nodes.post_drafter import HumanDrafter, PostDrafter
from flywheel.nodes.post_scheduler import PostScheduler
from flywheel.nodes.signal_analyzer import SignalAnalyzer, SignalVerdict
from flywheel.nodes.source_registry import SourceRegistry
from flywheel.nodes.source_scraper import SourceScraper
from flywheel.nodes.subscription_manager import SubscriptionManager
from flywheel.nodes.thesis_tracker import ThesisTracker
from flywheel.persistence.knowledge_store import (
    InMemoryKnowledgeStore,
    KnowledgeStore,
)
from flywheel.persistence.raw_record_store import (
    InMemoryRawRecordStore,
    RawRecordStore,
)
from flywheel.persistence.source_store import InMemorySourceStore, SourceStore

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

    # ── Live mode: real discovery via public ATS APIs + agentic site crawl ───
    # `config: {live: true}` scans the curated roster (ventures/lead_sources.yaml)
    # over the public Greenhouse/Lever/Ashby JSON APIs (free, no key). Enrichment
    # now *navigates the company's own site* via a best-first CrawlAgent (see
    # new_docs/scraping-engine.md). The executor is the in-house HttpxScraperClient
    # by default (no browser, no key) — or Firecrawl when FIRECRAWL_API_KEY is set
    # (for JS-heavy / anti-bot pages). The default (canned/offline) path is
    # unchanged, so tests + /topology stay deterministic.
    if config.get("live", False):
        scraper: WebScraperClient
        if os.environ.get("FIRECRAWL_API_KEY"):
            scraper = FirecrawlScraperClient.from_env() or HttpxScraperClient()
        else:
            scraper = HttpxScraperClient()
        return LeadSourcer(
            job_board=MultiATSJobBoardClient(load_roster(), store=InMemoryLeadStore()),
            crawler=CrawlAgent(scraper),
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


# ── Public-data ingestion cluster ──────────────────────────────────────────────
#
# The three ingestion nodes must share store instances within a single runtime
# (the scraper writes the raw store the builder reads; both share the source
# store). The registry builds nodes independently, so we hold a per-build bundle
# of shared stores. ``build_runtime_from_venture`` constructs all nodes in one
# pass; call ``reset_ingestion_stores()`` before each build to get fresh state.


class _IngestionStores:
    """Shared store instances wired across the three ingestion node builders."""

    def __init__(self) -> None:
        self.source: SourceStore = InMemorySourceStore()
        self.raw: RawRecordStore = InMemoryRawRecordStore()
        self.knowledge: KnowledgeStore = InMemoryKnowledgeStore()


_INGESTION_STORES = _IngestionStores()


def reset_ingestion_stores(
    *,
    source: SourceStore | None = None,
    raw: RawRecordStore | None = None,
    knowledge: KnowledgeStore | None = None,
) -> _IngestionStores:
    """Reset (or inject) the shared ingestion stores; returns the bundle.

    Pass real ``Sql*`` stores here (when ``DB_URL`` is set) to back the cluster
    with Neon; default is fresh in-memory fakes so the dev demo / tests stay
    zero-infra and deterministic.
    """
    global _INGESTION_STORES
    bundle = _IngestionStores()
    if source is not None:
        bundle.source = source
    if raw is not None:
        bundle.raw = raw
    if knowledge is not None:
        bundle.knowledge = knowledge
    _INGESTION_STORES = bundle
    return bundle


def ingestion_stores() -> _IngestionStores:
    """The current shared ingestion store bundle (for dev API introspection)."""
    return _INGESTION_STORES


def _source_registry(_config: dict[str, Any]) -> Node:
    return SourceRegistry(store=_INGESTION_STORES.source)


def _source_scraper(config: dict[str, Any]) -> Node:
    # Canned (default): offline fake fetch + heuristic inferencer, fully
    # deterministic. ``canned: false`` wires the real httpx client + LLM
    # inferencer (the agentic path) for live runs.
    if not config.get("canned", True):
        return SourceScraper(
            fetch_client=HttpxApiFetchClient(),
            inferencer=LLMInferencer(),
            source_store=_INGESTION_STORES.source,
            raw_store=_INGESTION_STORES.raw,
        )
    from flywheel.nodes._ingestion_seed import seed_bodies

    return SourceScraper(
        # Canned bodies for the six seed ATS sources, so a triggered scrape runs
        # end-to-end offline. The heuristic inferencer reads each shape generically.
        fetch_client=FakeApiFetchClient(seed_bodies()),
        inferencer=FakeInferencer(),
        source_store=_INGESTION_STORES.source,
        raw_store=_INGESTION_STORES.raw,
    )


def _knowledge_builder(_config: dict[str, Any]) -> Node:
    return KnowledgeBuilder(
        raw_store=_INGESTION_STORES.raw,
        knowledge_store=_INGESTION_STORES.knowledge,
        source_store=_INGESTION_STORES.source,
    )


def _insight_inferrer(config: dict[str, Any]) -> Node:
    # Agentic: reasons over the knowledge graph to surface founder-facing market
    # insights. Live wiring uses a real LLM (needs OPENAI_API_KEY); the default
    # canned path returns deterministic, signal-grounded insights so /topology
    # and tests run offline.
    if config.get("live", False):
        _require_env("OPENAI_API_KEY", "insight-inferrer", "live market inference")
        return InsightInferrer(
            knowledge_store=_INGESTION_STORES.knowledge,
            gateway=LiteLLMGateway(),
        )
    if not config.get("canned", True):
        return InsightInferrer(knowledge_store=_INGESTION_STORES.knowledge)
    gateway = FakeLLMGateway()
    gateway.register(InsightSet.__name__, _canned_insights)
    return InsightInferrer(knowledge_store=_INGESTION_STORES.knowledge, gateway=gateway)


def _canned_insights(prompt: str) -> dict[str, Any]:
    """Deterministic insights derived from the context embedded in the prompt.

    The prompt carries the ``open_roles`` and ``sentiment`` view rows; we parse
    company names heuristically so the canned gateway produces a plausible,
    grounded insight per company without a network call. Mirrors how the other
    canned agentic nodes build one builder per schema.
    """
    insights: list[dict[str, Any]] = []
    # Lead opportunities: any company appearing in the open-roles section.
    for company in _companies_after(prompt, "Open roles by company:"):
        insights.append(
            {
                "kind": "lead_opportunity",
                "company": company,
                "headline": f"{company} is hiring for content/brand — likely needs ghostwriting",
                "rationale": "An open content/brand/founder-comms role is a strong "
                "'they need help telling their story now' signal.",
                "recommended_action": f"Send {company} a tailored founder-ghostwriting pitch.",
                "confidence": 0.82,
                "urgent": True,
            }
        )
    # Risk signals: only companies with an actual negative-sentiment cluster.
    for company in _negative_companies_after(prompt, "Sentiment by company:"):
        insights.append(
            {
                "kind": "risk_signal",
                "company": company,
                "headline": f"Negative-review spike detected for {company}",
                "rationale": "A cluster of negative reviews signals churn/displacement "
                "risk — and an outreach opening.",
                "recommended_action": f"Reach out to {company}'s customers / monitor sentiment.",
                "confidence": 0.7,
                "urgent": True,
            }
        )
    return {"insights": insights}


def _companies_after(prompt: str, marker: str) -> list[str]:
    """Best-effort extraction of company names from a prompt section.

    The view rows are rendered as Python dicts in the prompt; we scan the lines
    of the marked section for ``'company': '<name>'`` occurrences. Deterministic
    and dependency-free.
    """
    import re

    start = prompt.find(marker)
    if start == -1:
        return []
    # Section ends at the next blank-line-separated marker (the other view).
    rest = prompt[start + len(marker):]
    end = rest.find("\n\n")
    section = rest if end == -1 else rest[:end]
    found = re.findall(r"'company':\s*'([^']+)'", section)
    # De-dup, preserve order, drop the "(unknown)" bucket.
    seen: list[str] = []
    for c in found:
        if c and c != "(unknown)" and c not in seen:
            seen.append(c)
    return seen


def _negative_companies_after(prompt: str, marker: str) -> list[str]:
    """Companies in the sentiment section whose negative_ratio exceeds a floor.

    The sentiment view rows render ``'company': '<name>', ... 'negative_ratio': <f>``;
    we pair each company with the next negative_ratio in the same row and keep
    those above a small threshold — so only real negative clusters become risks.
    """
    import re

    start = prompt.find(marker)
    if start == -1:
        return []
    rest = prompt[start + len(marker):]
    end = rest.find("\n\n")
    section = rest if end == -1 else rest[:end]
    # Match each row's company together with its negative_ratio.
    pairs = re.findall(
        r"'company':\s*'([^']+)'.*?'negative_ratio':\s*([0-9.]+)", section
    )
    out: list[str] = []
    for company, ratio in pairs:
        try:
            if company and company != "(unknown)" and float(ratio) >= 0.5:
                if company not in out:
                    out.append(company)
        except ValueError:
            continue
    return out


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
    # Public-data ingestion cluster.
    "source-registry": _source_registry,
    "source-scraper": _source_scraper,
    "knowledge-builder": _knowledge_builder,
    "insight-inferrer": _insight_inferrer,
}


def known_node_names() -> list[str]:
    return sorted(NODE_BUILDERS)


def build_node(name: str, config: dict[str, Any] | None = None) -> Node:
    """Instantiate a node by registry name with optional construction config."""
    factory = NODE_BUILDERS.get(name)
    if factory is None:
        raise KeyError(f"Unknown node {name!r}. Known: {', '.join(known_node_names())}")
    return factory(config or {})
