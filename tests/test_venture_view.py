from flywheel.devserver.topology import build_runtime, load_default_venture
from flywheel.venture.schema import FunctionSpec, NodeSpec, Venture
from flywheel.venture.view import function_view, lint_venture


def _live_describe():
    runtime, _, _ = build_runtime()
    return runtime.describe()


def test_function_view_groups_nodes_and_events() -> None:
    venture = load_default_venture()
    view = function_view(venture, _live_describe())
    by_name = {f["name"]: f for f in view}

    me = by_name["market-exploration"]
    assert "market-scanner" in me["nodes"]
    assert "signal-analyzer" in me["nodes"]
    # market-scanner reacts to research.requested and emits the landscape.
    assert "research.requested" in me["events_in"]
    assert "market.landscape.summarized" in me["events_out"]
    # signal-analyzer emits the verdict.
    assert "signal.verdict" in me["events_out"]


def test_function_view_reflects_overlap() -> None:
    venture = load_default_venture()
    view = function_view(venture, _live_describe())
    by_name = {f["name"]: f for f in view}
    # signal-analyzer appears in both market-exploration and customer-success.
    assert "signal-analyzer" in by_name["market-exploration"]["nodes"]
    assert "signal-analyzer" in by_name["customer-success"]["nodes"]


def test_lint_clean_for_postlineai() -> None:
    venture = load_default_venture()
    lint = lint_venture(venture, _live_describe())
    assert lint["unknown_nodes"] == []
    assert lint["inactive_nodes"] == []
    assert lint["config_conflicts"] == []


def test_lint_flags_unknown_node() -> None:
    venture = Venture(
        name="bad",
        functions=[FunctionSpec(name="x", nodes=[NodeSpec(name="not-a-real-node")])],
    )
    # Build describe from a runtime that doesn't have that node.
    lint = lint_venture(venture, _live_describe())
    assert "not-a-real-node" in lint["unknown_nodes"]


def test_lint_flags_config_conflict() -> None:
    venture = Venture(
        name="c",
        functions=[
            FunctionSpec(name="a", nodes=[NodeSpec(name="post-drafter", config={"impl": "human"})]),
            FunctionSpec(name="b", nodes=[NodeSpec(name="post-drafter", config={"impl": "agent"})]),
        ],
    )
    lint = lint_venture(venture, _live_describe())
    assert "post-drafter" in lint["config_conflicts"]
