from flywheel.devserver.topology import build_runtime, load_default_venture
from flywheel.venture.loader import build_runtime_from_venture, load_venture_by_name


def test_postlineai_yaml_loads_and_has_functions() -> None:
    v = load_venture_by_name("postlineai")
    assert v.name == "postlineai"
    fn_names = {f.name for f in v.functions}
    assert {"market-exploration", "gtm", "customer-success"} <= fn_names


def test_loaded_runtime_registers_all_step1_6_nodes() -> None:
    v = load_default_venture()
    runtime, _, _ = build_runtime_from_venture(v)
    names = {n.name for n in runtime.nodes}
    assert names == {
        # Steps 1–6 (the original walking skeleton).
        "market-scanner",
        "thesis-tracker",
        "pain-extractor",
        "ad-campaign-runner",
        "ad-analytics-collector",
        "signal-analyzer",
        "founder-notifier",
        "input-intake",
        "post-drafter",
        "human-review-queue",
        "post-scheduler",
        "subscription-manager",
        "post-analytics-collector",
        "customer-survey",
        # Outbound lead-gen function (PostlineAI customer acquisition).
        "lead-sourcer",
        "company-needs-analyzer",
        "pitch-generator",
    }


def test_overlapping_node_registered_once() -> None:
    # signal-analyzer is in both market-exploration and customer-success.
    v = load_default_venture()
    runtime, _, _ = build_runtime_from_venture(v)
    names = [n.name for n in runtime.nodes]
    assert names.count("signal-analyzer") == 1


def test_post_drafter_human_binding_from_yaml() -> None:
    v = load_default_venture()
    runtime, _, _ = build_runtime_from_venture(v)
    drafter = next(n for n in runtime.nodes if n.name == "post-drafter")
    assert drafter.version == "0.1.0-human"


def test_build_runtime_wrapper_matches_loader() -> None:
    # The public build_runtime() should produce the same node set as the loader.
    # 14 nodes from Steps 1–6 + 3 from the outbound lead-gen function = 17.
    runtime, _, _ = build_runtime()
    assert len(runtime.nodes) == 17
