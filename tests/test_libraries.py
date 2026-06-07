from pydantic import BaseModel

from flywheel.libraries.llm_gateway import FakeLLMGateway
from flywheel.libraries.semrush_client import FakeSemrushClient, KeywordVolume
from flywheel.libraries.web_search_client import FakeWebSearchClient, SearchResult


class Out(BaseModel):
    label: str = "default"


def test_fake_llm_gateway_uses_canned_builder() -> None:
    gw = FakeLLMGateway()
    gw.register("Out", lambda prompt: {"label": "canned"})
    parsed, completion = gw.complete("hello world", Out)
    assert parsed.label == "canned"
    assert completion.model == "fake/echo-1"
    assert completion.prompt_tokens == 2


def test_fake_llm_gateway_falls_back_to_schema_defaults() -> None:
    gw = FakeLLMGateway()
    parsed, _ = gw.complete("anything", Out)
    assert parsed.label == "default"


def test_fake_semrush_uses_fixture_then_pseudo_volume() -> None:
    fixtures = {"kw": KeywordVolume(keyword="kw", monthly_volume=999, competition=0.5)}
    client = FakeSemrushClient(fixtures=fixtures)
    out = client.keyword_volume(["kw", "other"])
    assert out[0].monthly_volume == 999
    # Deterministic pseudo-volume for unknown keyword.
    assert client.keyword_volume(["other"])[0].monthly_volume == out[1].monthly_volume


def test_fake_web_search_returns_fixture_and_generic() -> None:
    client = FakeWebSearchClient(
        results={"q": [SearchResult(title="t", url="u", snippet="s")]}
    )
    assert client.search("q")[0].title == "t"
    generic = client.search("unknown query")
    assert len(generic) == 1
    assert "unknown query" in generic[0].title


def test_fake_web_search_limit() -> None:
    results = [SearchResult(title=f"t{i}", url=f"u{i}", snippet="s") for i in range(5)]
    client = FakeWebSearchClient(results={"q": results})
    assert len(client.search("q", limit=2)) == 2
