"""The ``Inferencer`` seam — derived in the public-data ingestion step.

The agentic ``source-scraper`` is handed an *opaque* source. It must infer, at
runtime, **how to read it**: where the records live in the response, which field
is the unique id, which (if any) field is an incremental timestamp, and how the
source paginates. That inference is exactly the kind of "reason over data with
an LLM" work that makes a node *agentic* (``new_docs/layer1-nodes.md``).

Per the repo's seam pattern (mirrors ``core/agent.py`` and the ``Drafter`` seam):

  - ``Inferencer`` — the Protocol: ``infer(sample) -> IngestPlan``.
  - ``LLMInferencer`` — the real, agentic impl: one structured LLM call (via the
    ``Agent`` / ``llm-gateway`` seam) that returns a typed :class:`IngestPlan`.
  - ``FakeInferencer`` — deterministic, offline. Returns a canned plan when one
    is registered for a URL, otherwise falls back to a cheap **structural
    heuristic** so tests and the dev demo run with zero network and no LLM.

The same structural heuristic also backs the fake LLM gateway's canned builder,
so ``LLMInferencer`` is exercised end-to-end in tests without a real provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flywheel.core.agent import Agent, SingleCallAgent
from flywheel.libraries.api_fetch_client import FetchResult
from flywheel.libraries.llm_gateway import FakeLLMGateway, LLMGateway
from flywheel.persistence.models import IngestPlan, Pagination

# ── Structural heuristic (no LLM) ──────────────────────────────────────────────


def heuristic_plan(parsed: Any) -> IngestPlan:
    """Infer an :class:`IngestPlan` from a parsed body using cheap structure.

    Strategy (provider-agnostic):
      1. Locate the record list — the body itself if it's a list, else the
         longest list-of-objects value among the top-level keys.
      2. From the first record, pick an id field (prefer ``id``/``*_id``/``uuid``)
         and a timestamp field (prefer names containing
         ``updated``/``created``/``published``/``modified``/``date``/``time``).
      3. Guess timestamp format (epoch ms/s vs ISO) from the sample value.
      4. Default pagination to ``none`` (single snapshot) — the safe baseline.
    """
    record_path, records = _locate_records(parsed)
    first = records[0] if records and isinstance(records[0], dict) else {}
    id_field = _pick_id_field(first)
    ts_field, ts_format = _pick_timestamp_field(first)
    return IngestPlan(
        record_path=record_path,
        id_field=id_field,
        timestamp_field=ts_field,
        timestamp_format=ts_format,
        pagination=Pagination(kind="none"),
        content_type="json",
        confidence=0.6 if first else 0.2,
    )


def _locate_records(parsed: Any) -> tuple[str, list[Any]]:
    if isinstance(parsed, list):
        return "", parsed
    if isinstance(parsed, dict):
        best_key: str = ""
        best_list: list[Any] = []
        for key, value in parsed.items():
            if (
                isinstance(value, list)
                and value
                and isinstance(value[0], dict)
                and len(value) >= len(best_list)
            ):
                best_key, best_list = key, value
        return best_key, best_list
    return "", []


def _pick_id_field(record: Mapping[str, Any]) -> str:
    keys = list(record.keys())
    for preferred in ("id", "uuid", "_id", "key", "slug"):
        if preferred in record:
            return preferred
    for k in keys:
        if k.lower().endswith("id"):
            return k
    return "id"


def _pick_timestamp_field(record: Mapping[str, Any]) -> tuple[str, str]:
    candidates = ("updated", "modified", "published", "created", "date", "time")
    chosen = ""
    # Prefer "updated"-like fields over "created"-like ones (better cursor).
    for marker in candidates:
        for k in record:
            if marker in k.lower():
                chosen = k
                break
        if chosen:
            break
    if not chosen:
        return "", ""
    return chosen, _guess_format(record.get(chosen))


def _guess_format(value: Any) -> str:
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        n = int(value)
        # 13 digits ~ ms since epoch; 10 digits ~ seconds.
        return "epoch_ms" if n > 10_000_000_000 else "epoch_s"
    if isinstance(value, str) and ("-" in value and ("T" in value or ":" in value)):
        return "iso8601"
    return ""


# ── The seam ───────────────────────────────────────────────────────────────────


class Inferencer:
    """Protocol-shaped base: ``infer(FetchResult) -> IngestPlan``.

    Defined as a plain class (not ``Protocol``) so both impls can share nothing
    but the method name; nodes type against this.
    """

    def infer(self, sample: FetchResult) -> IngestPlan:  # pragma: no cover - interface
        raise NotImplementedError


class FakeInferencer(Inferencer):
    """Deterministic inferencer for tests / demo.

    Returns a canned plan when registered for the sample URL; otherwise applies
    the structural heuristic. This lets the whole ingestion flow run offline.
    """

    def __init__(self, canned: dict[str, IngestPlan] | None = None) -> None:
        self._canned = dict(canned or {})

    def register(self, url: str, plan: IngestPlan) -> None:
        self._canned[url] = plan

    def infer(self, sample: FetchResult) -> IngestPlan:
        if sample.url in self._canned:
            return self._canned[sample.url]
        return heuristic_plan(sample.parsed)


def _build_inference_prompt(inputs: Mapping[str, Any]) -> str:
    """Render the fetched sample into a single prompt for the SingleCallAgent."""
    return (
        "You are given a sample HTTP response body from an unknown data source.\n"
        "Infer how to ingest it: locate the list of records, the unique id "
        "field, an incremental timestamp field (if any), and the pagination "
        "mechanism. Return a structured IngestPlan.\n\n"
        f"URL: {inputs.get('url', '')}\n"
        f"Content-Type: {inputs.get('content_type', 'json')}\n"
        f"Body sample (truncated):\n{inputs.get('sample', '')[:4000]}\n"
    )


class LLMInferencer(Inferencer):
    """Agentic inferencer: one structured LLM call → :class:`IngestPlan`.

    Uses the same ``Agent`` / ``SingleCallAgent`` seam every agentic node uses,
    so the model is swappable and traced. Defaults to a ``FakeLLMGateway`` whose
    canned builder applies the structural heuristic — meaning the agentic path is
    fully exercised offline, and a real ``litellm`` gateway swaps in unchanged.
    """

    def __init__(
        self,
        *,
        gateway: LLMGateway | None = None,
        agent: Agent | None = None,
    ) -> None:
        gw = gateway or self._default_gateway()
        self._agent = agent or SingleCallAgent(gw, _build_inference_prompt)

    @staticmethod
    def _default_gateway() -> LLMGateway:
        # The fake gateway, by default, has no canned builder for IngestPlan, so
        # it would return schema defaults. Callers/tests register a builder (the
        # heuristic) to make the agentic path meaningful offline.
        return FakeLLMGateway()

    def infer(self, sample: FetchResult) -> IngestPlan:
        plan, _completion = self._agent.run(
            {
                "url": sample.url,
                "content_type": sample.content_type,
                "sample": sample.raw,
            },
            IngestPlan,
        )
        return plan
