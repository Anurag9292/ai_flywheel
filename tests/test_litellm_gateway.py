"""Tests for LiteLLMGateway (offline — litellm is mocked via sys.modules)."""

from __future__ import annotations

import sys
import types
from typing import Any

from pydantic import BaseModel

from flywheel.libraries.llm_gateway import DEFAULT_LLM_MODEL, LiteLLMGateway, LLMGateway


class _Schema(BaseModel):
    summary: str = ""
    score: float = 0.0


def _install_fake_litellm(
    monkeypatch: Any,
    *,
    content: str,
    cost: float = 0.0012,
    computed_cost: float = 0.0042,
) -> dict:
    """Install a fake `litellm` module that records the call and returns content.

    ``cost`` is what ``_hidden_params["response_cost"]`` carries; ``computed_cost``
    is what the ``litellm.completion_cost`` fallback returns.
    """
    captured: dict[str, Any] = {}

    def completion(**kwargs: Any) -> Any:
        captured.update(kwargs)
        msg = types.SimpleNamespace(content=content)
        choice = types.SimpleNamespace(message=msg)
        usage = types.SimpleNamespace(prompt_tokens=11, completion_tokens=7)
        resp = types.SimpleNamespace(choices=[choice], usage=usage)
        resp._hidden_params = {"response_cost": cost}
        return resp

    def completion_cost(completion_response: Any = None, **_: Any) -> float:
        return computed_cost

    fake = types.ModuleType("litellm")
    fake.completion = completion  # type: ignore[attr-defined]
    fake.completion_cost = completion_cost  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "litellm", fake)
    return captured


def test_litellm_gateway_parses_structured_output(monkeypatch: Any) -> None:
    captured = _install_fake_litellm(
        monkeypatch, content='{"summary": "great fit", "score": 0.9}'
    )
    gw = LiteLLMGateway(model="gpt-4o-mini")
    parsed, completion = gw.complete("analyze this", _Schema)

    assert isinstance(parsed, _Schema)
    assert parsed.summary == "great fit"
    assert parsed.score == 0.9
    # Real Completion fields populated from the response.
    assert completion.model == "gpt-4o-mini"
    assert completion.prompt_tokens == 11
    assert completion.completion_tokens == 7
    assert completion.cost_usd == 0.0012
    # Prompt + response_format(schema) actually sent.
    assert captured["model"] == "gpt-4o-mini"
    assert captured["response_format"]["json_schema"]["name"] == "_Schema"
    assert any(m["content"] == "analyze this" for m in captured["messages"])


def test_litellm_cost_falls_back_to_completion_cost(monkeypatch: Any) -> None:
    # _hidden_params carries 0.0 (the real-run symptom) → fall back to
    # litellm.completion_cost(), which computes from model + token usage.
    _install_fake_litellm(
        monkeypatch,
        content='{"summary": "x", "score": 0.1}',
        cost=0.0,
        computed_cost=0.0042,
    )
    gw = LiteLLMGateway()
    _parsed, completion = gw.complete("x", _Schema)
    assert completion.cost_usd == 0.0042


def test_litellm_gateway_default_model(monkeypatch: Any) -> None:
    monkeypatch.delenv("FLYWHEEL_LLM_MODEL", raising=False)
    gw = LiteLLMGateway()
    assert gw.model == DEFAULT_LLM_MODEL


def test_litellm_gateway_model_from_env(monkeypatch: Any) -> None:
    monkeypatch.setenv("FLYWHEEL_LLM_MODEL", "claude-3-5-haiku")
    gw = LiteLLMGateway()
    assert gw.model == "claude-3-5-haiku"


def test_litellm_gateway_satisfies_protocol() -> None:
    assert isinstance(LiteLLMGateway(), LLMGateway)


def test_litellm_gateway_parse_failure_raises(monkeypatch: Any) -> None:
    _install_fake_litellm(monkeypatch, content="not json at all")
    gw = LiteLLMGateway()
    try:
        gw.complete("x", _Schema)
    except Exception as exc:  # noqa: BLE001
        assert "json" in type(exc).__name__.lower() or "Validation" in type(exc).__name__
    else:
        raise AssertionError("expected a parse error")
