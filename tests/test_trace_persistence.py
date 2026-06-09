"""The dev runtime persists trace rows to a JSONL file when given a trace_log."""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.core.events import Event
from flywheel.devserver.topology import build_runtime


def test_publish_appends_jsonl_rows(tmp_path: Path) -> None:
    log = tmp_path / "traces.jsonl"
    runtime, bus, _recorder = build_runtime(trace_log=log, keep_in_memory=True)

    # A simple, offline trigger (default fake venture) that fans out through
    # several nodes — each invocation should append one JSON line.
    bus.publish(
        Event(
            type="lead-search.requested",
            venture_id="postlineai",
            payload={"criteria": {"keywords": ["content"], "limit": 3}},
        )
    )

    assert log.exists()
    lines = [line for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 1
    rows = [json.loads(line) for line in lines]
    # Every row is a well-formed trace with the fields the timeline/cost need.
    for row in rows:
        assert "node" in row
        assert "correlation_id" in row
        assert "latency_ms" in row
        assert "cost_usd" in row
    # The lead-sourcer step was recorded.
    assert any(r["node"] == "lead-sourcer" for r in rows)


def test_trace_log_appends_across_runs(tmp_path: Path) -> None:
    log = tmp_path / "traces.jsonl"
    runtime, bus, _ = build_runtime(trace_log=log, keep_in_memory=True)

    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))
    first = len(log.read_text(encoding="utf-8").splitlines())
    bus.publish(Event(type="lead-search.requested", venture_id="v", payload={}))
    second = len(log.read_text(encoding="utf-8").splitlines())

    # Appended, not overwritten.
    assert second > first
