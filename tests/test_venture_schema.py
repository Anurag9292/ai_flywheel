import pytest

from flywheel.venture.registry import build_node, known_node_names
from flywheel.venture.schema import FunctionSpec, NodeSpec, Venture


def _venture() -> Venture:
    return Venture(
        name="demo",
        functions=[
            FunctionSpec(
                name="market-exploration",
                nodes=[NodeSpec(name="market-scanner"), NodeSpec(name="signal-analyzer")],
            ),
            FunctionSpec(
                name="customer-success",
                # signal-analyzer overlaps with market-exploration on purpose.
                nodes=[NodeSpec(name="customer-survey"), NodeSpec(name="signal-analyzer")],
            ),
        ],
    )


def test_node_specs_dedupes_overlapping_nodes() -> None:
    v = _venture()
    names = sorted(s.name for s in v.node_specs())
    assert names == ["customer-survey", "market-scanner", "signal-analyzer"]


def test_functions_for_reports_overlap() -> None:
    v = _venture()
    assert set(v.functions_for("signal-analyzer")) == {
        "market-exploration",
        "customer-success",
    }
    assert v.functions_for("customer-survey") == ["customer-success"]


def test_first_config_wins_on_conflict() -> None:
    v = Venture(
        name="x",
        functions=[
            FunctionSpec(name="a", nodes=[NodeSpec(name="post-drafter", config={"impl": "human"})]),
            FunctionSpec(name="b", nodes=[NodeSpec(name="post-drafter", config={"impl": "agent"})]),
        ],
    )
    specs = {s.name: s for s in v.node_specs()}
    assert specs["post-drafter"].config == {"impl": "human"}


def test_registry_builds_every_known_node() -> None:
    for name in known_node_names():
        node = build_node(name)
        assert node.name == name


def test_registry_unknown_node_raises() -> None:
    with pytest.raises(KeyError):
        build_node("does-not-exist")


def test_post_drafter_unimplemented_impl_raises() -> None:
    with pytest.raises(ValueError):
        build_node("post-drafter", {"impl": "agent-v1"})
