"""End-to-end ingestion flow through the PostlineAI venture runtime.

Exercises the whole cluster wired from ``ventures/postlineai.yaml`` via the
registry's shared in-memory stores:

    source.register.requested (6 seeds)
        → sources.updated
    scrape.requested / tick.daily
        → source.records.ingested (per source, resumable + idempotent)
    source.records.ingested
        → knowledge.updated (KG entities/edges + materialized views)
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.timers import TimerSource
from flywheel.devserver.topology import build_runtime
from flywheel.nodes._ingestion_seed import SEED_SOURCES, seed_register_payload
from flywheel.venture.registry import ingestion_stores


def _build():
    runtime, bus, recorder = build_runtime(keep_in_memory=True)
    return runtime, bus, recorder


def test_full_ingestion_pipeline_register_scrape_build() -> None:
    _, bus, _ = _build()
    ingested: list[Event] = []
    knowledge: list[Event] = []
    bus.subscribe("source.records.ingested", ingested.append)
    bus.subscribe("knowledge.updated", knowledge.append)

    # Registering the six seed sources emits ``sources.updated``, which the
    # scraper reacts to — so registration alone drives the first full scrape.
    bus.publish(
        Event(
            type="source.register.requested",
            venture_id="postlineai",
            payload=seed_register_payload(),
        )
    )

    # One ingested event per source on the initial scrape.
    assert len(ingested) == len(SEED_SOURCES)
    total_new = sum(e.payload["new_count"] for e in ingested)
    assert total_new == 7  # 2+1+1 (lever) + 1 (gh) + 1+1 (ashby)

    # Knowledge built from the new records (raw store → KG + views).
    assert knowledge, "expected knowledge.updated to fire"
    store = ingestion_stores().knowledge
    companies = {c.key for c in store.entities(type="Company", venture_id="postlineai")}
    assert {"Mindtickle", "Nium", "Scaleway", "Webflow", "PostHog", "Vercel"} <= companies

    view = store.get_view("open_roles_by_company", "postlineai")
    assert view is not None
    by_company = {r["company"]: r["open_roles"] for r in view.rows}
    assert by_company["Mindtickle"] == 2
    assert by_company["Webflow"] == 1


def test_scheduled_rerun_resumes_and_is_idempotent() -> None:
    _, bus, _ = _build()
    ingested: list[Event] = []
    bus.subscribe("source.records.ingested", ingested.append)

    bus.publish(
        Event(
            type="source.register.requested",
            venture_id="postlineai",
            payload=seed_register_payload(),
        )
    )
    first_total = sum(e.payload["new_count"] for e in ingested)
    assert first_total == 7

    # A scheduled re-run (tick.daily) re-fetches the same snapshots; idempotent
    # storage means zero new records the second time.
    ingested.clear()
    TimerSource(bus).tick_daily(venture_id="postlineai")
    assert sum(e.payload["new_count"] for e in ingested) == 0


def test_knowledge_updates_incrementally_across_runs() -> None:
    _, bus, _ = _build()
    knowledge: list[Event] = []
    bus.subscribe("knowledge.updated", knowledge.append)

    bus.publish(
        Event(
            type="source.register.requested",
            venture_id="postlineai",
            payload=seed_register_payload(),
        )
    )
    # The builder processes new rows incrementally as each source ingests; the
    # cumulative new_records across the initial scrape is 7.
    assert sum(e.payload["new_records"] for e in knowledge) == 7

    # Second scheduled run: nothing new ingested → builder finds no new rows and
    # does not emit again.
    before = len(knowledge)
    TimerSource(bus).tick_daily(venture_id="postlineai")
    assert len(knowledge) == before
