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
