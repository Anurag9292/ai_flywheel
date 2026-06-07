"""End-to-end demo of PostlineAI Step 2 — desk research (the agentic path).

Run it:

    uv run python demo_step2.py

It wires the in-memory bus, the trace-recorder, and the *agentic*
``market-scanner`` node (with offline fake libraries + a fake LLM gateway), then
publishes a ``research.requested`` event. You should see:

  1. the node call its libraries, run its agent, and emit
     ``market.landscape.summarized`` (event-driven flow, agentic node), and
  2. a ``trace.captured`` row — proving an agentic node is observed *identically*
     to the dumb ``thesis-tracker`` from Step 1.

It also prints ``runtime.describe()`` — the code-derived topology that the
visualization (``new_docs/visualization.md``) renders.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.core import Event, InMemoryEventBus, Runtime, TraceRecorder
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.libraries.semrush_client import FakeSemrushClient, KeywordVolume
from flywheel.libraries.web_search_client import FakeWebSearchClient, SearchResult
from flywheel.nodes.market_scanner import MarketMap, MarketScanner

TRACE_LOG = Path("traces.jsonl")
VENTURE = "postlineai"


def main() -> None:
    if TRACE_LOG.exists():
        TRACE_LOG.unlink()

    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=TRACE_LOG)
    runtime = Runtime(bus, recorder)

    # Fake libraries seeded so the run is deterministic and offline.
    semrush = FakeSemrushClient(
        fixtures={
            "linkedin ghostwriter": KeywordVolume(
                keyword="linkedin ghostwriter", monthly_volume=12000, competition=0.6
            )
        }
    )
    web = FakeWebSearchClient(
        results={
            "AI LinkedIn ghostwriting competitors": [
                SearchResult(
                    title="Taplio",
                    url="https://taplio.com",
                    snippet="AI LinkedIn tool, ~$39/mo.",
                ),
                SearchResult(
                    title="Human ghostwriter agency",
                    url="https://example-agency.com",
                    snippet="Done-for-you posts, ~$5k/mo.",
                ),
            ]
        }
    )

    # Teach the fake gateway what a MarketMap should look like for this prompt.
    gateway = FakeLLMGateway()
    gateway.register(
        MarketMap.__name__,
        lambda prompt: {
            "summary": "Crowded at the cheap end (Taplio ~$39) and the premium "
            "end ($5k agencies); a gap exists at $499 for AI-with-a-human-touch.",
            "competitors": [
                {"name": "Taplio", "url": "https://taplio.com", "pricing": "$39/mo",
                 "positioning": "self-serve AI tool"},
                {"name": "Agencies", "pricing": "$5k/mo", "positioning": "human DFY"},
            ],
            "top_keywords": ["linkedin ghostwriter", "b2b founder content"],
        },
    )

    scanner = MarketScanner(semrush=semrush, web_search=web, gateway=gateway)
    runtime.register(scanner)

    def watch(event: Event) -> None:
        mm = MarketMap.model_validate(event.payload)
        print(f"  ↳ emitted {event.type}")
        print(f"    summary: {mm.summary}")
        print(f"    competitors: {[c.name for c in mm.competitors]}")
        print(f"    top_keywords: {mm.top_keywords}")

    bus.subscribe("market.landscape.summarized", watch)

    print("Publishing research.requested for PostlineAI...\n")
    bus.publish(Event(
        type="research.requested",
        venture_id=VENTURE,
        payload={
            "thesis": "B2B founders will pay $499/mo for AI LinkedIn ghostwriting",
            "keywords": ["linkedin ghostwriter", "b2b founder content"],
            "competitor_query": "AI LinkedIn ghostwriting competitors",
        },
    ))

    print(f"\nAutomatic trace ({TRACE_LOG}):")
    for line in TRACE_LOG.read_text().splitlines():
        t = json.loads(line)
        if t["node"] != "market-scanner":
            continue
        print(f"  - {t['node']} v{t['node_version']} reacted to {t['trigger_type']} "
              f"in {t['latency_ms']}ms, emitted {t['emitted_types']}")

    print("\nCode-derived topology (runtime.describe()):")
    print(json.dumps(runtime.describe(), indent=2))


if __name__ == "__main__":
    main()
