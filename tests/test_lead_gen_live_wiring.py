"""Tests for the roster loader and the registry's live lead-sourcer wiring."""

from __future__ import annotations

from typing import Any

from flywheel.libraries.job_board_client import (
    FakeJobBoardClient,
    MultiATSJobBoardClient,
    load_roster,
)
from flywheel.libraries.web_scraper_client import (
    FakeWebScraperClient,
    FirecrawlScraperClient,
)
from flywheel.nodes.lead_sourcer import LeadSourcer
from flywheel.venture.registry import build_node


def test_load_roster_default_file_parses() -> None:
    roster = load_roster()
    assert len(roster) >= 1
    atss = {c.ats for c in roster}
    assert atss <= {"greenhouse", "lever", "ashby"}
    assert all(c.token for c in roster)


def test_load_roster_missing_file_returns_empty(tmp_path: Any) -> None:
    assert load_roster(str(tmp_path / "nope.yaml")) == []


def test_default_lead_sourcer_uses_fakes() -> None:
    node = build_node("lead-sourcer", {})
    assert isinstance(node, LeadSourcer)
    # Default (canned) path: fake clients, deterministic, offline.
    assert isinstance(node._job_board, FakeJobBoardClient)  # type: ignore[attr-defined]
    assert isinstance(node._scraper, FakeWebScraperClient)  # type: ignore[attr-defined]


def test_live_lead_sourcer_uses_multi_ats(monkeypatch: Any) -> None:
    # No FIRECRAWL_API_KEY → live discovery is real (ATS) but enrichment falls
    # back to the offline fake scraper.
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    node = build_node("lead-sourcer", {"live": True})
    assert isinstance(node, LeadSourcer)
    assert isinstance(node._job_board, MultiATSJobBoardClient)  # type: ignore[attr-defined]
    assert isinstance(node._scraper, FakeWebScraperClient)  # type: ignore[attr-defined]


def test_live_lead_sourcer_uses_firecrawl_when_key_set(monkeypatch: Any) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    node = build_node("lead-sourcer", {"live": True})
    assert isinstance(node._scraper, FirecrawlScraperClient)  # type: ignore[attr-defined]
