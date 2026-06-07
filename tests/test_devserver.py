from fastapi.testclient import TestClient

from flywheel.devserver.app import app

client = TestClient(app)


def setup_function() -> None:
    # Each test starts from a clean in-memory trace state.
    client.post("/api/reset")


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_topology_endpoint_returns_describe_shape() -> None:
    r = client.get("/api/topology")
    assert r.status_code == 200
    topo = r.json()
    names = {n["name"] for n in topo["nodes"]}
    assert {"thesis-tracker", "market-scanner"} <= names
    assert "llm-gateway" in topo["libraries"]
    assert topo["substrate"]["name"] == "trace-recorder"


def test_publish_triggers_real_multistep_run() -> None:
    r = client.post(
        "/api/publish",
        json={
            "type": "research.requested",
            "venture_id": "postlineai",
            "payload": {
                "thesis": "B2B founders pay $499/mo",
                "keywords": ["linkedin ghostwriter"],
                "competitor_query": "AI LinkedIn ghostwriting competitors",
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    chain = body["chain"]
    nodes = [s["node"] for s in chain["steps"]]
    # The real chain: market-scanner then thesis-tracker reacting to it.
    assert nodes == ["market-scanner", "thesis-tracker"]
    assert chain["steps"][0]["is_start"] is True
    assert chain["steps"][-1]["is_end"] is True


def test_traces_reflects_published_runs_and_reset() -> None:
    client.post("/api/publish", json={"type": "research.requested", "payload": {}})
    body = client.get("/api/traces").json()
    assert body["count"] >= 1
    assert len(body["chains"]) >= 1

    client.post("/api/reset")
    assert client.get("/api/traces").json()["count"] == 0


def test_evidence_event_runs_thesis_tracker_only() -> None:
    r = client.post(
        "/api/publish",
        json={
            "type": "evidence.collected",
            "payload": {"assumption": "willing_to_pay_499", "supports": True},
        },
    )
    nodes = [s["node"] for s in r.json()["chain"]["steps"]]
    assert nodes == ["thesis-tracker"]


def test_build_chain_orders_and_links_causally() -> None:
    from flywheel.devserver.app import _build_chain

    # Two steps in one run: scanner emits e1, which triggers tracker.
    steps = [
        {
            "captured_at": "2026-01-01T00:00:00.002+00:00",
            "node": "thesis-tracker",
            "trigger_event_id": "e1",
            "trigger_type": "market.landscape.summarized",
            "emitted_event_ids": ["e2"],
        },
        {
            "captured_at": "2026-01-01T00:00:00.001+00:00",
            "node": "market-scanner",
            "trigger_event_id": "root",
            "trigger_type": "research.requested",
            "emitted_event_ids": ["e1"],
        },
    ]
    chain = _build_chain("c1", steps)
    s = chain["steps"]

    # Sorted chronologically: scanner first.
    assert [x["node"] for x in s] == ["market-scanner", "thesis-tracker"]
    assert s[0]["seq"] == 0 and s[1]["seq"] == 1
    # Causality: tracker's parent is the scanner step.
    assert s[0]["parent_step"] is None and s[0]["is_start"] is True
    assert s[1]["parent_step"] == 0
    # Start is consumed downstream (not end); tracker is the end.
    assert s[0]["is_end"] is False
    assert s[1]["is_end"] is True
