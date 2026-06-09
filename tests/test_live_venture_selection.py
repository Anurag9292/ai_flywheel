"""Tests for env-var venture selection + the LIVE/FAKE mode (offline).

These never hit the network: a live ``lead-sourcer`` is asserted by the *type*
of job-board client it was constructed with (``MultiATSJobBoardClient``), not by
running a real fetch.
"""

from __future__ import annotations

from typing import Any

from flywheel.devserver.topology import (
    DEFAULT_VENTURE,
    build_runtime,
    load_default_venture,
    runtime_mode,
    selected_venture_name,
)
from flywheel.libraries.job_board_client import (
    FakeJobBoardClient,
    MultiATSJobBoardClient,
)
from flywheel.nodes.lead_sourcer import LeadSourcer


def _lead_sourcer(runtime: Any) -> LeadSourcer:
    node = next(n for n in runtime.nodes if n.name == "lead-sourcer")
    assert isinstance(node, LeadSourcer)
    return node


# ── env-var selection ─────────────────────────────────────────────────────────


def test_default_selection_is_postlineai(monkeypatch: Any) -> None:
    monkeypatch.delenv("FLYWHEEL_VENTURE", raising=False)
    assert selected_venture_name() == DEFAULT_VENTURE


def test_env_var_overrides_selection(monkeypatch: Any) -> None:
    monkeypatch.setenv("FLYWHEEL_VENTURE", "postlineai-live")
    assert selected_venture_name() == "postlineai-live"


def test_empty_env_var_falls_back_to_default(monkeypatch: Any) -> None:
    monkeypatch.setenv("FLYWHEEL_VENTURE", "")
    assert selected_venture_name() == DEFAULT_VENTURE


# ── default venture: FAKE discovery ──────────────────────────────────────────


def test_default_venture_is_fake_mode() -> None:
    venture = load_default_venture("postlineai")
    assert runtime_mode(venture) == "fake"


def test_default_runtime_builds_fake_lead_sourcer() -> None:
    runtime, _, _ = build_runtime(venture_name="postlineai")
    node = _lead_sourcer(runtime)
    assert isinstance(node._job_board, FakeJobBoardClient)  # type: ignore[attr-defined]


# ── live venture: REAL discovery (asserted by client type, no network) ────────


def test_live_venture_is_live_mode() -> None:
    venture = load_default_venture("postlineai-live")
    assert runtime_mode(venture) == "live"
    # Same composition as the default otherwise (same function names).
    default = load_default_venture("postlineai")
    assert {f.name for f in venture.functions} == {f.name for f in default.functions}


def test_live_runtime_builds_multi_ats_lead_sourcer(monkeypatch: Any) -> None:
    # No FIRECRAWL_API_KEY → discovery is real (ATS) but enrichment is the fake
    # scraper. Crucially we only check the *type* — no fetch is performed.
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    runtime, _, _ = build_runtime(venture_name="postlineai-live")
    node = _lead_sourcer(runtime)
    assert isinstance(node._job_board, MultiATSJobBoardClient)  # type: ignore[attr-defined]


def test_live_venture_registers_same_node_set_as_default() -> None:
    # The live variant must be identical in roster — only lead-sourcer config
    # differs — so the topology graph/UI looks the same.
    live, _, _ = build_runtime(venture_name="postlineai-live")
    default, _, _ = build_runtime(venture_name="postlineai")
    assert {n.name for n in live.nodes} == {n.name for n in default.nodes}
