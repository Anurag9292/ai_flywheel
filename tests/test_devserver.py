import json

from fastapi.testclient import TestClient

from flywheel.devserver.app import app

client = TestClient(app)


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


def test_traces_endpoint_groups_by_correlation(tmp_path, monkeypatch) -> None:
    # Point the app at a temp trace log with two rows sharing a correlation id.
    log = tmp_path / "traces.jsonl"
    rows = [
        {"node": "a", "correlation_id": "c1", "trigger_type": "x"},
        {"node": "b", "correlation_id": "c1", "trigger_type": "y"},
        {"node": "c", "correlation_id": "c2", "trigger_type": "z"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))

    import flywheel.devserver.app as appmod

    monkeypatch.setattr(appmod, "DEFAULT_TRACE_LOG", log)

    r = client.get("/api/traces")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 3
    chains = {c["correlation_id"]: c for c in body["chains"]}
    assert len(chains["c1"]["steps"]) == 2
    assert len(chains["c2"]["steps"]) == 1


def test_traces_endpoint_empty_when_no_log(tmp_path, monkeypatch) -> None:
    import flywheel.devserver.app as appmod

    monkeypatch.setattr(appmod, "DEFAULT_TRACE_LOG", tmp_path / "none.jsonl")
    r = client.get("/api/traces")
    assert r.json()["count"] == 0


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
