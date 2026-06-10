"""Tests for the ``Inferencer`` seam (heuristic, fake, and agentic LLM impls).

These also use small *captured-shape* samples mirroring the three ATS providers
the user supplied (Lever array, Greenhouse ``{jobs, meta}``, Ashby
``{jobs, apiVersion}``) — used purely as **test data**, never as encoded
adapters. The inferencer must figure each out generically.
"""

from __future__ import annotations

from flywheel.core.inferencer import (
    FakeInferencer,
    LLMInferencer,
    heuristic_plan,
)
from flywheel.libraries.api_fetch_client import FetchResult
from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.persistence.models import IngestPlan

# ── sample bodies (shape only) ──────────────────────────────────────────────────

LEVER = [
    {"id": "uuid-1", "text": "Role A", "createdAt": 1776772338840, "categories": {}},
    {"id": "uuid-2", "text": "Role B", "createdAt": 1776772300000, "categories": {}},
]
GREENHOUSE = {
    "jobs": [
        {"id": 7951428, "title": "AE", "updated_at": "2026-06-09T12:55:09-04:00"},
        {"id": 7951429, "title": "SE", "updated_at": "2026-06-08T10:00:00-04:00"},
    ],
    "meta": {"total": 2},
}
ASHBY = {
    "apiVersion": "1",
    "jobs": [
        {"id": "a-1", "title": "Eng", "publishedAt": "2026-04-21T06:53:22.089+00:00"},
    ],
}


def _result(url: str, body) -> FetchResult:
    import json

    return FetchResult(url=url, parsed=body, raw=json.dumps(body), content_type="json")


def test_heuristic_lever_array_root() -> None:
    plan = heuristic_plan(LEVER)
    assert plan.record_path == ""  # body is the list
    assert plan.id_field == "id"
    assert plan.timestamp_field == "createdAt"
    assert plan.timestamp_format == "epoch_ms"


def test_heuristic_greenhouse_finds_jobs_and_updated_at() -> None:
    plan = heuristic_plan(GREENHOUSE)
    assert plan.record_path == "jobs"
    assert plan.id_field == "id"
    # "updated" is preferred over "created"-style; ISO format detected.
    assert plan.timestamp_field == "updated_at"
    assert plan.timestamp_format == "iso8601"


def test_heuristic_ashby_finds_jobs_and_publishedAt() -> None:
    plan = heuristic_plan(ASHBY)
    assert plan.record_path == "jobs"
    assert plan.id_field == "id"
    assert plan.timestamp_field == "publishedAt"
    assert plan.timestamp_format == "iso8601"


def test_fake_inferencer_prefers_canned_over_heuristic() -> None:
    canned = IngestPlan(record_path="data", id_field="slug")
    inf = FakeInferencer({"https://x": canned})
    assert inf.infer(_result("https://x", LEVER)).id_field == "slug"
    # Unknown URL falls back to heuristic.
    assert inf.infer(_result("https://y", LEVER)).id_field == "id"


def test_llm_inferencer_runs_through_agent_seam_with_heuristic_builder() -> None:
    # Wire the fake gateway's canned builder to the structural heuristic so the
    # agentic path produces a meaningful plan fully offline.
    import json

    gateway = FakeLLMGateway()

    def build(prompt: str) -> dict:
        # The prompt embeds the body sample; recover it and run the heuristic.
        marker = "Body sample (truncated):\n"
        sample = prompt.split(marker, 1)[1] if marker in prompt else "[]"
        try:
            parsed = json.loads(sample)
        except json.JSONDecodeError:
            parsed = []
        return heuristic_plan(parsed).model_dump()

    gateway.register(IngestPlan.__name__, build)
    inf = LLMInferencer(gateway=gateway)
    plan = inf.infer(_result("https://api.greenhouse.io/x", GREENHOUSE))
    assert plan.record_path == "jobs"
    assert plan.timestamp_field == "updated_at"
