"""Tests for the roster loader and the registry's live lead-gen wiring.

LIVE is "all-or-nothing, fail-loud": a live node uses the real backend and
raises if its required key is missing — no fake fallback. These tests assert
the wiring by *type* (and that missing keys raise); they never call a real
backend.
"""

from __future__ import annotations

from typing import Any

import pytest

from flywheel.agents.crawl_agent import CrawlAgent
from flywheel.libraries.job_board_client import (
    FakeJobBoardClient,
    MultiATSJobBoardClient,
    load_roster,
)
from flywheel.libraries.llm_gateway import FakeLLMGateway, LiteLLMGateway
from flywheel.libraries.web_scraper_client import (
    FakeWebScraperClient,
    FirecrawlScraperClient,
    HttpxScraperClient,
)
from flywheel.nodes.company_needs_analyzer import CompanyNeedsAnalyzer
from flywheel.nodes.lead_sourcer import LeadSourcer
from flywheel.nodes.pitch_generator import PitchGenerator
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


def test_live_lead_sourcer_uses_httpx_crawler_without_key(monkeypatch: Any) -> None:
    # No key needed: live discovery is real (ATS), and the agentic site crawl
    # uses the in-house HttpxScraperClient (no browser) by default.
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    node = build_node("lead-sourcer", {"live": True})
    assert isinstance(node, LeadSourcer)
    assert isinstance(node._job_board, MultiATSJobBoardClient)  # type: ignore[attr-defined]
    crawler = node._crawler  # type: ignore[attr-defined]
    assert isinstance(crawler, CrawlAgent)
    assert isinstance(crawler._scraper, HttpxScraperClient)  # type: ignore[attr-defined]


def test_live_lead_sourcer_uses_firecrawl_executor_when_key_set(monkeypatch: Any) -> None:
    # When FIRECRAWL_API_KEY is set, the crawl executor is Firecrawl (for
    # JS-heavy / anti-bot pages) — still behind the same CrawlAgent.
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    node = build_node("lead-sourcer", {"live": True})
    crawler = node._crawler  # type: ignore[attr-defined]
    assert isinstance(crawler, CrawlAgent)
    assert isinstance(crawler._scraper, FirecrawlScraperClient)  # type: ignore[attr-defined]


# ── live LLM nodes (require OPENAI_API_KEY; real gateway by type) ─────────────


def test_default_llm_nodes_use_fake_gateway() -> None:
    cna = build_node("company-needs-analyzer", {})
    pg = build_node("pitch-generator", {})
    assert isinstance(cna, CompanyNeedsAnalyzer)
    assert isinstance(pg, PitchGenerator)
    # Default canned path → SingleCallAgent over a FakeLLMGateway.
    assert isinstance(cna._agent._gateway, FakeLLMGateway)  # type: ignore[attr-defined]
    assert isinstance(pg._agent._gateway, FakeLLMGateway)  # type: ignore[attr-defined]


def test_live_llm_nodes_require_openai_key(monkeypatch: Any) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_node("company-needs-analyzer", {"live": True})
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_node("pitch-generator", {"live": True})


def test_live_llm_nodes_use_litellm_when_key_set(monkeypatch: Any) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    cna = build_node("company-needs-analyzer", {"live": True})
    pg = build_node("pitch-generator", {"live": True})
    assert isinstance(cna._agent._gateway, LiteLLMGateway)  # type: ignore[attr-defined]
    assert isinstance(pg._agent._gateway, LiteLLMGateway)  # type: ignore[attr-defined]
