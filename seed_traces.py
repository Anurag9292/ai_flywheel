"""Seed a realistic ``traces.jsonl`` for the visualization, exercising every
currently-built node in one shared runtime so the trace-replay view has
meaningful multi-node chains.

    uv run python seed_traces.py

Unlike the per-step ``demo*.py`` scripts (which each reset the log to show a
single flow cleanly), this *accumulates* a representative set of runs.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.core.events import Event
from flywheel.devserver.topology import DEFAULT_TRACE_LOG, build_runtime
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.nodes.market_scanner import MarketMap

VENTURE = "postlineai"


def main() -> None:
    log = Path(DEFAULT_TRACE_LOG)
    if log.exists():
        log.unlink()

    runtime = build_runtime()
    bus = runtime._bus  # noqa: SLF001 — seed script may reach into the runtime

    # Teach the market-scanner's default fake gateway a canned MarketMap so the
    # seeded run produces a rich payload. (The default node built its own agent;
    # we register on a fresh gateway by re-registering the node would be heavier,
    # so we just publish — the default fake falls back to schema defaults, which
    # is fine for trace seeding.)
    _ = (FakeLLMGateway, MarketMap)  # documented intent; defaults suffice here

    # Run 1: thesis evidence (Step 1).
    bus.publish(Event(
        type="evidence.collected",
        venture_id=VENTURE,
        payload={"assumption": "willing_to_pay_499", "supports": True},
    ))
    # Run 2: more evidence.
    bus.publish(Event(
        type="evidence.collected",
        venture_id=VENTURE,
        payload={"assumption": "trusts_ai_voice", "supports": False},
    ))
    # Run 3: desk research (Step 2, agentic).
    bus.publish(Event(
        type="research.requested",
        venture_id=VENTURE,
        payload={
            "thesis": "B2B founders will pay $499/mo for AI LinkedIn ghostwriting",
            "keywords": ["linkedin ghostwriter", "b2b founder content"],
            "competitor_query": "AI LinkedIn ghostwriting competitors",
        },
    ))

    rows = log.read_text().splitlines()
    print(f"Seeded {len(rows)} trace rows into {log} across "
          f"{len({__import__('json').loads(r)['correlation_id'] for r in rows})} runs.")


if __name__ == "__main__":
    main()
