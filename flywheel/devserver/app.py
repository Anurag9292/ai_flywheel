"""FastAPI dev introspection app.

Endpoints (read-only):

- ``GET /api/health``   — liveness.
- ``GET /api/topology`` — ``Runtime.describe()``: the code-derived node/event
  graph (visualization View 1).
- ``GET /api/traces``   — parsed ``trace.captured`` rows from ``traces.jsonl``,
  grouped into causal chains by ``correlation_id`` (visualization View 2).

Run it:

    uv run uvicorn flywheel.devserver.app:app --reload --port 8000

CORS is open to localhost dev origins only; this server must never be exposed
publicly (see the caveat in ``new_docs/visualization.md``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flywheel.devserver.topology import DEFAULT_TRACE_LOG, build_runtime

app = FastAPI(
    title="AI Flywheel — Dev Introspection",
    description="Read-only topology + trace introspection for visualization. Dev only.",
    version="0.1.0",
)

# Next dev server origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# A single runtime describes the current topology. Rebuilt cheaply per process.
_runtime = build_runtime()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/topology")
def topology() -> dict[str, Any]:
    """The code-derived topology graph."""
    return _runtime.describe()


def _load_traces(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


@app.get("/api/traces")
def traces() -> dict[str, Any]:
    """Parsed trace.captured rows, plus chains grouped by correlation_id.

    Each chain is one causal run (a published event + every node reaction it
    triggered), which is exactly what the trace-replay view animates.
    """
    rows = _load_traces(DEFAULT_TRACE_LOG)

    chains: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        chains.setdefault(row.get("correlation_id", "unknown"), []).append(row)

    return {
        "count": len(rows),
        "traces": rows,
        "chains": [
            {"correlation_id": cid, "steps": steps}
            for cid, steps in chains.items()
        ],
    }
