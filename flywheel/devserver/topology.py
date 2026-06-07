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
from flywheel.nodes.market_scanner import MarketMap, MarketScanner
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

    runtime.register(_demo_market_scanner())
    runtime.register(ThesisTracker())

    return runtime, bus, recorder
