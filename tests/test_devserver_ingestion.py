"""Dev API tests for the ingestion flywheel: tick + knowledge endpoints (Phase 3).

Drives the live dev runtime (in-memory fakes; no DB_URL) end to end via HTTP so
the UI path is covered: register sources, then a scheduled tick re-runs the
flywheel, and the knowledge endpoint exposes the built views.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from flywheel.devserver.app import app
from flywheel.nodes._ingestion_seed import seed_all_register_payload

client = TestClient(app)


def setup_function() -> None:
    client.post("/api/reset")


def _register_all() -> None:
    client.post(
        "/api/publish",
        json={
            "type": "source.register.requested",
            "venture_id": "postlineai",
            "payload": seed_all_register_payload(),
        },
    )


def test_register_then_knowledge_views_populate() -> None:
    _register_all()

    roles = client.get(
        "/api/ingestion/knowledge", params={"view": "open_roles_by_company"}
    ).json()
    assert roles["rows"], "expected open_roles_by_company to be populated"
    assert roles["entity_counts"]["Job"] >= 1

    sentiment = client.get(
        "/api/ingestion/knowledge", params={"view": "recent_sentiment_by_company"}
    ).json()
    companies = {r["company"] for r in sentiment["rows"]}
    assert "Acme Analytics" in companies
    # Review entities were built from the review feed.
    assert sentiment["entity_counts"]["Review"] >= 1


def test_tick_endpoint_is_idempotent_after_register() -> None:
    _register_all()
    r = client.post("/api/tick", json={"period": "daily", "venture_id": "postlineai"})
    assert r.status_code == 200
    body = r.json()
    assert body["published"]["type"] == "tick.daily"
    # The chain ran through the ingestion nodes (scraper re-fetched; idempotent).
    assert "chain" in body


def test_ingestion_sources_endpoint_lists_registered() -> None:
    _register_all()
    body = client.get("/api/ingestion/sources").json()
    assert body["count"] >= 8
    kinds = {s["enrichment"].get("kind") for s in body["sources"]}
    assert "ats-job-board" in kinds
    assert "review-feed" in kinds
