"""Seed a realistic ``traces.jsonl`` with ONE coherent multi-step PostlineAI run
so the chronological timeline / trace-replay view has a real start→progress→end
sequence to play.

    uv run python seed_traces.py

The wired chain (reuse by subscription — see new_docs/venture-walkthrough.md):

    research.requested
        → market-scanner            (calls semrush / web-search / llm)
            → market.landscape.summarized
                → thesis-tracker     (reacts to the landscape as evidence)
                    → thesis.state.updated   (END)

Unlike the per-step ``demo*.py`` scripts (which reset the log to show a single
flow cleanly), this builds the canonical end-to-end run.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.libraries.semrush_client import FakeSemrushClient, KeywordVolume
from flywheel.libraries.web_search_client import FakeWebSearchClient, SearchResult
from flywheel.nodes.market_scanner import MarketMap, MarketScanner
from flywheel.nodes.thesis_tracker import ThesisTracker

DEFAULT_TRACE_LOG = Path("traces.jsonl")
VENTURE = "postlineai"


def build_seed_runtime(trace_log: Path) -> tuple[Runtime, InMemoryEventBus]:
    """Wire a runtime whose market-scanner produces a rich, gap-naming landscape
    (so thesis-tracker reacts), with thesis-tracker subscribed downstream.
    """
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=trace_log)
    runtime = Runtime(bus, recorder)

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
    scanner = MarketScanner(
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

    runtime.register(scanner)
    runtime.register(ThesisTracker())  # subscribes to market.landscape.summarized
    return runtime, bus


def main() -> None:
    log = Path(DEFAULT_TRACE_LOG)
    if log.exists():
        log.unlink()

    _runtime, bus = build_seed_runtime(log)

    # The single start event — the founder kicks off desk research.
    bus.publish(Event(
        type="research.requested",
        venture_id=VENTURE,
        payload={
            "thesis": "B2B founders will pay $499/mo for AI LinkedIn ghostwriting",
            "keywords": ["linkedin ghostwriter", "b2b founder content"],
            "competitor_query": "AI LinkedIn ghostwriting competitors",
        },
    ))

    rows = [json.loads(line) for line in log.read_text().splitlines()]
    corr = {r["correlation_id"] for r in rows}
    print(f"Seeded {len(rows)} trace rows in {len(corr)} run(s):")
    for r in rows:
        print(f"  {r['captured_at']}  {r['node']:<16} reacted to "
              f"{r['trigger_type']:<28} → {r['emitted_types']}")


if __name__ == "__main__":
    main()
