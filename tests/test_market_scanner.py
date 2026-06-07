from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.libraries.semrush_client import FakeSemrushClient
from flywheel.libraries.web_search_client import FakeWebSearchClient, SearchResult
from flywheel.nodes.market_scanner import MarketMap, MarketScanner


def _runtime(tmp_path, scanner):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(scanner)
    return bus, runtime


def _scanner_with_canned_map():
    gw = FakeLLMGateway()
    gw.register(
        "MarketMap",
        lambda prompt: {
            "summary": "gap at $499",
            "competitors": [{"name": "Taplio", "pricing": "$39/mo"}],
            "top_keywords": ["linkedin ghostwriter"],
        },
    )
    return MarketScanner(
        semrush=FakeSemrushClient(),
        web_search=FakeWebSearchClient(
            results={"q": [SearchResult(title="Taplio", url="https://taplio.com", snippet="ai")]}
        ),
        gateway=gw,
    )


def test_market_scanner_emits_structured_landscape(tmp_path) -> None:
    scanner = _scanner_with_canned_map()
    bus, _ = _runtime(tmp_path, scanner)
    out: list[Event] = []
    bus.subscribe("market.landscape.summarized", out.append)

    bus.publish(Event(
        type="research.requested",
        venture_id="postlineai",
        payload={"thesis": "t", "keywords": ["linkedin ghostwriter"], "competitor_query": "q"},
    ))

    assert len(out) == 1
    mm = MarketMap.model_validate(out[0].payload)
    assert mm.summary == "gap at $499"
    assert mm.competitors[0].name == "Taplio"
    assert mm.top_keywords == ["linkedin ghostwriter"]


def test_market_scanner_inherits_correlation_id(tmp_path) -> None:
    scanner = _scanner_with_canned_map()
    bus, _ = _runtime(tmp_path, scanner)
    out: list[Event] = []
    bus.subscribe("market.landscape.summarized", out.append)

    trigger = Event(type="research.requested", venture_id="postlineai", payload={"thesis": "t"})
    bus.publish(trigger)

    assert out[0].correlation_id == trigger.correlation_id


def test_market_scanner_runs_with_defaults(tmp_path) -> None:
    # No injected libs/gateway: uses all fakes; falls back to MarketMap defaults.
    scanner = MarketScanner()
    bus, _ = _runtime(tmp_path, scanner)
    out: list[Event] = []
    bus.subscribe("market.landscape.summarized", out.append)

    bus.publish(Event(type="research.requested", venture_id="v", payload={"thesis": "t"}))

    assert len(out) == 1
    MarketMap.model_validate(out[0].payload)  # valid, default-filled
