"""Tests for the timer substrate."""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.inferencer import FakeInferencer
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.core.timers import TimerSource
from flywheel.libraries.api_fetch_client import FakeApiFetchClient
from flywheel.nodes.source_scraper import SourceScraper
from flywheel.persistence.models import Source
from flywheel.persistence.raw_record_store import InMemoryRawRecordStore
from flywheel.persistence.source_store import InMemorySourceStore


def test_timer_publishes_tick_event() -> None:
    bus = InMemoryEventBus()
    got: list[Event] = []
    bus.subscribe("tick.daily", got.append)
    timer = TimerSource(bus)

    ev = timer.tick_daily(venture_id="v")
    assert ev.type == "tick.daily"
    assert got and got[0].venture_id == "v"


def test_timer_minute_and_custom_period() -> None:
    bus = InMemoryEventBus()
    got: list[str] = []
    bus.subscribe("tick.minute", lambda e: got.append(e.type))
    bus.subscribe("tick.hourly", lambda e: got.append(e.type))
    timer = TimerSource(bus)
    timer.tick_minute(venture_id="v")
    timer.tick("hourly", venture_id="v")
    assert got == ["tick.minute", "tick.hourly"]


def test_tick_daily_drives_source_scraper(tmp_path) -> None:
    # The timer substrate makes scheduled re-scrapes real: a tick.daily triggers
    # the scraper exactly like an explicit scrape.requested would.
    url = "https://api.example.com/jobs"
    sources = InMemorySourceStore()
    sources.upsert(Source(id="s1", venture_id="v", url=url))
    raw = InMemoryRawRecordStore()
    fetch = FakeApiFetchClient({url: [{"id": "1", "createdAt": 1}]})
    node = SourceScraper(
        fetch_client=fetch,
        inferencer=FakeInferencer(),
        source_store=sources,
        raw_store=raw,
    )

    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(node)
    out: list[Event] = []
    bus.subscribe("source.records.ingested", out.append)

    TimerSource(bus).tick_daily(venture_id="v")
    assert out and out[0].payload["new_count"] == 1
