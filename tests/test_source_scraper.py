"""Tests for ``source-scraper`` — inference caching, resume, idempotency."""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.inferencer import FakeInferencer
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.api_fetch_client import FakeApiFetchClient
from flywheel.nodes.source_scraper import SourceScraper, _fingerprint
from flywheel.persistence.models import IngestPlan, Source
from flywheel.persistence.raw_record_store import InMemoryRawRecordStore
from flywheel.persistence.source_store import InMemorySourceStore

URL = "https://api.example.com/jobs"

# Two records with epoch-ms timestamps (Lever-shape array at root).
BODY_V1 = [
    {"id": "1", "text": "Role A", "createdAt": 1000},
    {"id": "2", "text": "Role B", "createdAt": 2000},
]
BODY_V2 = BODY_V1 + [{"id": "3", "text": "Role C", "createdAt": 3000}]


def _runtime(tmp_path, node):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(node)
    return bus, runtime


def _make(source_store, raw_store, fetch, infer=None):
    return SourceScraper(
        fetch_client=fetch,
        inferencer=infer or FakeInferencer(),
        source_store=source_store,
        raw_store=raw_store,
    )


def test_scrape_ingests_records_and_emits(tmp_path) -> None:
    sources = InMemorySourceStore()
    sources.upsert(Source(id="s1", venture_id="v", url=URL))
    raw = InMemoryRawRecordStore()
    fetch = FakeApiFetchClient({URL: BODY_V1})
    node = _make(sources, raw, fetch)
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("source.records.ingested", out.append)

    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))

    assert out[0].payload["new_count"] == 2
    assert raw.max_seq("s1") == 2


def test_rescrape_is_idempotent(tmp_path) -> None:
    sources = InMemorySourceStore()
    sources.upsert(Source(id="s1", venture_id="v", url=URL))
    raw = InMemoryRawRecordStore()
    fetch = FakeApiFetchClient({URL: BODY_V1})
    node = _make(sources, raw, fetch)
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("source.records.ingested", out.append)

    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))
    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))

    assert out[0].payload["new_count"] == 2
    assert out[1].payload["new_count"] == 0  # nothing new on re-scrape
    assert raw.max_seq("s1") == 2


def test_resume_picks_up_only_new_records(tmp_path) -> None:
    sources = InMemorySourceStore()
    sources.upsert(Source(id="s1", venture_id="v", url=URL))
    raw = InMemoryRawRecordStore()
    fetch = FakeApiFetchClient({URL: BODY_V1})
    node = _make(sources, raw, fetch)
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("source.records.ingested", out.append)

    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))
    # The source now grows; next scheduled run should add only the new record.
    fetch.add(URL, BODY_V2)
    bus.publish(Event(type="tick.daily", venture_id="v", payload={}))

    assert out[0].payload["new_count"] == 2
    assert out[1].payload["new_count"] == 1
    assert raw.max_seq("s1") == 3


def test_inference_cached_and_reinferred_on_drift(tmp_path) -> None:
    sources = InMemorySourceStore()
    sources.upsert(Source(id="s1", venture_id="v", url=URL))
    raw = InMemoryRawRecordStore()
    fetch = FakeApiFetchClient({URL: BODY_V1})

    # A counting inferencer so we can assert it's only called when needed.
    class CountingInferencer(FakeInferencer):
        calls = 0

        def infer(self, sample):  # type: ignore[override]
            CountingInferencer.calls += 1
            return super().infer(sample)

    node = _make(sources, raw, fetch, infer=CountingInferencer())
    bus, _ = _runtime(tmp_path, node)

    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))
    assert CountingInferencer.calls == 1
    # Same shape next run → cached plan reused, no re-inference.
    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))
    assert CountingInferencer.calls == 1
    # Shape drift (object instead of array) → re-infer.
    fetch.add(URL, {"jobs": [{"id": "9", "updated_at": "2026-01-01T00:00:00Z"}]})
    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))
    assert CountingInferencer.calls == 2


def test_human_hints_override_inference(tmp_path) -> None:
    # Inference would pick id_field="id"; the human hint forces "text".
    sources = InMemorySourceStore()
    sources.upsert(Source(id="s1", venture_id="v", url=URL, hints={"id_field": "text"}))
    raw = InMemoryRawRecordStore()
    fetch = FakeApiFetchClient({URL: BODY_V1})
    node = _make(sources, raw, fetch)
    bus, _ = _runtime(tmp_path, node)

    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))
    rows = raw.read_since(0)
    # external_id now comes from the "text" field per the hint.
    assert {r.external_id for r in rows} == {"Role A", "Role B"}


def test_low_confidence_parks_for_human(tmp_path) -> None:
    sources = InMemorySourceStore()
    sources.upsert(Source(id="s1", venture_id="v", url=URL))
    raw = InMemoryRawRecordStore()
    # A body the heuristic can't read (no list of objects) → low confidence.
    fetch = FakeApiFetchClient({URL: {"weird": 1}})
    node = SourceScraper(
        fetch_client=fetch,
        inferencer=FakeInferencer(),  # heuristic → confidence 0.2
        source_store=sources,
        raw_store=raw,
        min_confidence=0.5,
    )
    bus, _ = _runtime(tmp_path, node)
    parked: list[Event] = []
    ingested: list[Event] = []
    bus.subscribe("source.inference.low_confidence", parked.append)
    bus.subscribe("source.records.ingested", ingested.append)

    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))
    assert len(parked) == 1
    assert parked[0].tags.get("requires_human") is True
    assert len(ingested) == 0  # parked, not ingested


def test_canned_plan_via_inferencer_for_known_url(tmp_path) -> None:
    sources = InMemorySourceStore()
    sources.upsert(Source(id="s1", venture_id="v", url=URL))
    raw = InMemoryRawRecordStore()
    fetch = FakeApiFetchClient({URL: BODY_V1})
    infer = FakeInferencer(
        {URL: IngestPlan(id_field="id", timestamp_field="createdAt", timestamp_format="epoch_ms")}
    )
    node = _make(sources, raw, fetch, infer=infer)
    bus, _ = _runtime(tmp_path, node)
    out: list[Event] = []
    bus.subscribe("source.records.ingested", out.append)
    bus.publish(Event(type="scrape.requested", venture_id="v", payload={"source_id": "s1"}))
    assert out[0].payload["new_count"] == 2


def test_fingerprint_changes_with_shape() -> None:
    assert _fingerprint(BODY_V1) == _fingerprint(BODY_V2)  # same record keys
    assert _fingerprint(BODY_V1) != _fingerprint({"jobs": []})
