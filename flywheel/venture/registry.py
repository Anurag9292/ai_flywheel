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

from collections.abc import Callable
from typing import Any

from flywheel.core.node import Node
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.libraries.semrush_client import FakeSemrushClient, KeywordVolume
from flywheel.libraries.web_search_client import FakeWebSearchClient, SearchResult
from flywheel.nodes.ad_analytics_collector import AdAnalyticsCollector
from flywheel.nodes.ad_campaign_runner import AdCampaignRunner
from flywheel.nodes.customer_survey import CustomerSurvey
from flywheel.nodes.founder_notifier import FounderNotifier
from flywheel.nodes.human_review_queue import HumanReviewQueue
from flywheel.nodes.input_intake import InputIntake
from flywheel.nodes.market_scanner import MarketMap, MarketScanner
from flywheel.nodes.pain_extractor import PainExtractor, PainReport
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
    "human-review-queue": lambda _c: HumanReviewQueue(),
    "post-scheduler": lambda _c: PostScheduler(),
    "subscription-manager": lambda _c: SubscriptionManager(),
    "post-analytics-collector": lambda _c: PostAnalyticsCollector(),
    "customer-survey": lambda _c: CustomerSurvey(),
}


def known_node_names() -> list[str]:
    return sorted(NODE_BUILDERS)


def build_node(name: str, config: dict[str, Any] | None = None) -> Node:
    """Instantiate a node by registry name with optional construction config."""
    factory = NODE_BUILDERS.get(name)
    if factory is None:
        raise KeyError(f"Unknown node {name!r}. Known: {', '.join(known_node_names())}")
    return factory(config or {})
