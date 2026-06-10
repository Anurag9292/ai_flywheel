"""End-to-end demo of the self-inferring public-data ingestion flywheel.

Run it:

    uv run python demo_ingestion.py

The market-exploration / discovery loop, end to end:

  source.register.requested (job boards + review feeds)
    → source-registry stores them (auto-enriching kind from the URL)
    → sources.updated
  → source-scraper hits each source, INFERS its schema generically, stores raw
    records idempotently (resumable cursor)
    → source.records.ingested
  → knowledge-builder folds NEW records into a knowledge graph + materialized
    views (jobs → open_roles_by_company; reviews → recent_sentiment_by_company)
    → knowledge.updated
  → insight-inferrer reasons over the graph and emits decoupled market insights:
      • a company hiring for content/brand → likely needs ghostwriting (lead)
      • a cluster of negative reviews → churn/displacement risk (risk signal)
    → market.insight (+ signal.verdict for the high-value ones)
  → founder-notifier routes the urgent ones to Slack + email (reused, no new
    notification machinery).

If ``DB_URL`` is set (e.g. in .env), the whole thing persists to Neon; otherwise
it runs on in-memory fakes. Either way the chain is identical and deterministic
(the LLM steps default to canned gateways).
"""

from __future__ import annotations

from pathlib import Path

from flywheel.env import load_dotenv_if_present

# Pick up a repo-root .env so DB_URL (and any live keys) are found.
load_dotenv_if_present()

from flywheel.core.events import Event  # noqa: E402
from flywheel.core.timers import TimerSource  # noqa: E402
from flywheel.devserver.topology import build_runtime  # noqa: E402
from flywheel.nodes._ingestion_seed import seed_all_register_payload  # noqa: E402
from flywheel.venture.registry import ingestion_stores  # noqa: E402

TRACE_LOG = Path("traces.jsonl")
VENTURE = "postlineai"


def _print_insights(insights: list[Event]) -> None:
    leads = [e for e in insights if e.payload.get("kind") == "lead_opportunity"]
    risks = [e for e in insights if e.payload.get("kind") == "risk_signal"]
    print(f"\nMarket insights: {len(insights)}  ({len(leads)} leads, {len(risks)} risks)")
    for e in insights:
        p = e.payload
        tag = "LEAD " if p["kind"] == "lead_opportunity" else "RISK "
        urgent = " [URGENT]" if p.get("urgent") else ""
        print(f"  {tag}{p['company']:<18}{urgent}")
        print(f"        {p['headline']}")
        print(f"        → {p['recommended_action']}")


def main() -> None:
    if TRACE_LOG.exists():
        TRACE_LOG.unlink()

    import os

    backend = "Neon (DB_URL set)" if os.environ.get("DB_URL") else "in-memory fakes"
    print(f"Ingestion flywheel demo — backend: {backend}\n")

    runtime, bus, _recorder = build_runtime(TRACE_LOG, keep_in_memory=True)

    insights: list[Event] = []
    notified: list[Event] = []
    ingested: list[Event] = []
    bus.subscribe("market.insight", insights.append)
    bus.subscribe("founder.notified", notified.append)
    bus.subscribe("source.records.ingested", ingested.append)

    # Run 1: register both source domains → drives the first full scrape→build→infer.
    print("Run 1 — registering job boards + review feeds, scraping, inferring schemas, "
          "building the graph, and surfacing founder insights…")
    bus.publish(
        Event(
            type="source.register.requested",
            venture_id=VENTURE,
            payload=seed_all_register_payload(),
        )
    )

    total_new = sum(e.payload["new_count"] for e in ingested)
    print(f"\nIngested {total_new} new records across {len(ingested)} sources.")

    store = ingestion_stores().knowledge
    roles = store.get_view("open_roles_by_company", VENTURE)
    sentiment = store.get_view("recent_sentiment_by_company", VENTURE)
    if roles:
        print("\nopen_roles_by_company:")
        for r in roles.rows:
            print(f"  {r['company']:<18} {r['open_roles']} open role(s)")
    if sentiment:
        print("\nrecent_sentiment_by_company:")
        for r in sentiment.rows:
            print(f"  {r['company']:<18} {r['negative']}/{r['total']} negative "
                  f"(neg ratio {r['negative_ratio']})")

    _print_insights(insights)
    print(f"\nFounder notifications sent: {len(notified)} "
          f"({sum(1 for n in notified if n.payload.get('urgent'))} urgent → Slack+email).")

    # Run 2: a scheduled re-run is idempotent — same snapshots add zero records.
    print("\nRun 2 — scheduled tick.daily (resume + idempotency check)…")
    ingested.clear()
    TimerSource(bus).tick_daily(venture_id=VENTURE)
    print(f"New records on the scheduled re-run: "
          f"{sum(e.payload['new_count'] for e in ingested)} (expected 0).")


if __name__ == "__main__":
    main()
