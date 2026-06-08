"""Builds the runtime used by the dev introspection server.

It registers the nodes that exist today (Step 1 + Step 2) so ``describe()``
returns a meaningful graph AND so events published via ``/api/publish`` produce
a real, deterministic multi-step run. As new nodes are built, register them
here (or, once ``topology.yaml`` exists in Layer 2, derive this from a venture
topology).

The market-scanner here is wired with a canned (offline) gateway so a triggered
``research.requested`` yields a gap-naming landscape — which the thesis-tracker
then reacts to. This is the fake/real seam working as intended: real bus + real
nodes, fake leaf I/O.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.core.events import InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
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
from flywheel.nodes.post_drafter import PostDrafter
from flywheel.nodes.post_scheduler import PostScheduler
from flywheel.nodes.signal_analyzer import SignalAnalyzer, SignalVerdict
from flywheel.nodes.subscription_manager import SubscriptionManager
from flywheel.nodes.thesis_tracker import ThesisTracker

DEFAULT_TRACE_LOG = Path("traces.jsonl")


def _demo_market_scanner() -> MarketScanner:
    """A market-scanner whose fake gateway returns a rich, gap-naming landscape
    so triggered runs produce the full chain deterministically.
    """
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


def _demo_pain_extractor() -> PainExtractor:
    """A pain-extractor whose fake gateway returns rich, deterministic pains."""
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


def _demo_signal_analyzer() -> SignalAnalyzer:
    """A signal-analyzer whose fake gateway returns a strong verdict so the
    Step-4 decision chain runs end-to-end deterministically.
    """
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


def build_runtime(
    trace_log: Path | None = None,
    *,
    keep_in_memory: bool = False,
) -> tuple[Runtime, InMemoryEventBus, TraceRecorder]:
    """Wire a Runtime with all currently-built nodes registered.

    Returns the runtime, its bus (so the API can publish onto it), and the
    recorder (so the API can read live in-memory traces / reset them).

    Pass ``trace_log`` to also append rows to a JSONL file (headless scripts);
    the dev API uses ``keep_in_memory=True`` and no file.
    """
    bus = InMemoryEventBus()
    recorder = TraceRecorder(
        bus, log_path=trace_log, keep_in_memory=keep_in_memory
    )
    runtime = Runtime(bus, recorder)

    # Step 1–2: research + thesis tracking.
    runtime.register(_demo_market_scanner())
    runtime.register(ThesisTracker())
    # Step 3: discovery → pain extraction (feeds thesis-tracker by subscription).
    runtime.register(_demo_pain_extractor())
    # Step 4: the ad-test decision loop.
    runtime.register(AdCampaignRunner())
    runtime.register(AdAnalyticsCollector())
    runtime.register(_demo_signal_analyzer())
    runtime.register(FounderNotifier())
    # Step 5: Wizard-of-Oz product flow (human-in-the-loop drafting).
    runtime.register(InputIntake())
    runtime.register(PostDrafter())  # defaults to HumanDrafter
    runtime.register(HumanReviewQueue())
    runtime.register(PostScheduler())
    runtime.register(SubscriptionManager())
    # Step 6: measure what's working (post engagement + customer surveys).
    runtime.register(PostAnalyticsCollector())
    runtime.register(CustomerSurvey())

    return runtime, bus, recorder


def find_review_queue(runtime: Runtime) -> HumanReviewQueue | None:
    """Return the registered human-review-queue, if any (for the dev review API)."""
    for node in runtime.nodes:
        if isinstance(node, HumanReviewQueue):
            return node
    return None
