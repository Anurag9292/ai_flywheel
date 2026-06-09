"""Tests for ``company-needs-analyzer``."""

from __future__ import annotations

from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.nodes.company_needs_analyzer import (
    CompanyNeedsAnalyzer,
    CompanyNeedsReport,
)


def _runtime(tmp_path, node):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    runtime.register(node)
    return bus, runtime


def _canned_analyzer() -> CompanyNeedsAnalyzer:
    gw = FakeLLMGateway()
    gw.register(
        "CompanyNeedsReport",
        lambda prompt: {
            "companies": [
                {
                    "company": "Acme",
                    "top_need": "founder content",
                    "buying_signals": ["hiring head of content"],
                    "fit_score": 0.9,
                    "pitch_angle": "we already do this",
                    "contact_email": "careers@acme.example.com",
                }
            ]
        },
    )
    return CompanyNeedsAnalyzer(gateway=gw)


def test_emits_structured_report(tmp_path) -> None:
    bus, _ = _runtime(tmp_path, _canned_analyzer())
    out: list[Event] = []
    bus.subscribe("company.needs.profiled", out.append)

    bus.publish(
        Event(
            type="companies.discovered",
            venture_id="postlineai",
            payload={
                "icp": "B2B SaaS founders",
                "offer": "$499/mo ghostwriting",
                "companies": [
                    {
                        "company": "Acme",
                        "contact_email": "careers@acme.example.com",
                        "postings": [
                            {"title": "Head of Content", "description": "founder content"}
                        ],
                    }
                ],
            },
        )
    )

    assert len(out) == 1
    report = CompanyNeedsReport.model_validate(out[0].payload)
    assert report.companies[0].company == "Acme"
    assert report.companies[0].top_need == "founder content"
    assert report.companies[0].fit_score == 0.9


def test_carries_through_contact_email_when_agent_omits_it(tmp_path) -> None:
    # The canned builder returns no contact_email; the node should fall back to
    # the upstream lead's email so downstream pitches still know who to mail.
    gw = FakeLLMGateway()
    gw.register(
        "CompanyNeedsReport",
        lambda prompt: {
            "companies": [
                {
                    "company": "Acme",
                    "top_need": "founder content",
                    "fit_score": 0.5,
                }
            ]
        },
    )
    bus, _ = _runtime(tmp_path, CompanyNeedsAnalyzer(gateway=gw))
    out: list[Event] = []
    bus.subscribe("company.needs.profiled", out.append)

    bus.publish(
        Event(
            type="companies.discovered",
            venture_id="v",
            payload={
                "companies": [
                    {"company": "Acme", "contact_email": "hiring@acme.example.com"}
                ]
            },
        )
    )

    report = CompanyNeedsReport.model_validate(out[0].payload)
    assert report.companies[0].contact_email == "hiring@acme.example.com"


def test_runs_with_defaults(tmp_path) -> None:
    # No injected gateway → uses the FakeLLMGateway with no canned builder, so
    # the agent falls back to schema defaults. The node must still emit one event.
    bus, _ = _runtime(tmp_path, CompanyNeedsAnalyzer())
    out: list[Event] = []
    bus.subscribe("company.needs.profiled", out.append)

    bus.publish(
        Event(type="companies.discovered", venture_id="v", payload={"companies": []})
    )

    assert len(out) == 1
    CompanyNeedsReport.model_validate(out[0].payload)
