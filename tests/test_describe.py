from flywheel.core.events import InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.nodes.market_scanner import MarketScanner
from flywheel.nodes.thesis_tracker import ThesisTracker


def _runtime(tmp_path):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    return Runtime(bus, recorder)


def test_describe_lists_nodes_with_metadata(tmp_path) -> None:
    rt = _runtime(tmp_path)
    rt.register(ThesisTracker())
    rt.register(MarketScanner())

    topo = rt.describe()
    by_name = {n["name"]: n for n in topo["nodes"]}

    assert by_name["thesis-tracker"]["kind"] == "dumb"
    assert by_name["thesis-tracker"]["emits"] == ["thesis.state.updated"]
    assert by_name["market-scanner"]["kind"] == "agentic"
    assert "llm-gateway" in by_name["market-scanner"]["calls"]


def test_describe_collects_libraries(tmp_path) -> None:
    rt = _runtime(tmp_path)
    rt.register(MarketScanner())
    topo = rt.describe()
    assert set(topo["libraries"]) == {"semrush-client", "web-search-client", "llm-gateway"}


def test_describe_builds_event_and_edge_graph(tmp_path) -> None:
    rt = _runtime(tmp_path)
    rt.register(MarketScanner())
    topo = rt.describe()

    events = {e["type"]: e for e in topo["events"]}
    assert events["research.requested"]["reacted_by"] == ["market-scanner"]
    assert events["market.landscape.summarized"]["emitted_by"] == ["market-scanner"]

    edge_kinds = {(e["source"], e["target"], e["kind"]) for e in topo["edges"]}
    assert ("research.requested", "market-scanner", "reacts") in edge_kinds
    assert ("market-scanner", "market.landscape.summarized", "emits") in edge_kinds
    assert ("market-scanner", "llm-gateway", "calls") in edge_kinds


def test_describe_lint_flags_orphans(tmp_path) -> None:
    rt = _runtime(tmp_path)
    rt.register(MarketScanner())
    topo = rt.describe()

    # market-scanner emits market.landscape.summarized but nothing reacts here.
    assert "market.landscape.summarized" in topo["lint"]["orphan_emitted"]
    # research.requested is reacted to but no registered node emits it.
    assert "research.requested" in topo["lint"]["unproduced_reacted"]


def test_describe_substrate_wraps_all(tmp_path) -> None:
    rt = _runtime(tmp_path)
    rt.register(ThesisTracker())
    rt.register(MarketScanner())
    topo = rt.describe()
    assert topo["substrate"]["name"] == "trace-recorder"
    assert set(topo["substrate"]["wraps"]) == {"thesis-tracker", "market-scanner"}
