"""``market-scanner`` — derived in PostlineAI Step 2 (the first *agentic* node).

> *The venture needs to: read competitor pages and synthesize a positioning
> landscape — pricing, claims, audience.*

An **event-driven node** that reacts to ``research.requested``, *calls* two
library tools (``semrush-client`` for keyword volume, ``web-search-client`` for
competitor discovery), feeds the gathered evidence to its ``Agent``, and emits
``market.landscape.summarized`` carrying a structured ``MarketMap``.

- **Reacts to:** ``research.requested``.
- **Calls:** ``semrush-client``, ``web-search-client``, ``llm-gateway`` (via its
  ``Agent``).
- **Emits:** ``market.landscape.summarized``.
- **Kind:** agentic.

Per the approved Step-2 design, the node **declares its own agent** (injected in
``__init__``, defaulting to a ``SingleCallAgent`` over a ``FakeLLMGateway``), so
``NodeContext`` / ``Runtime`` stay unchanged from Step 1. The agent is still
swappable via constructor injection.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from flywheel.core.agent import Agent, SingleCallAgent
from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.llm_gateway import FakeLLMGateway, LLMGateway
from flywheel.libraries.semrush_client import FakeSemrushClient, SemrushClient
from flywheel.libraries.web_search_client import (
    FakeWebSearchClient,
    WebSearchClient,
)


class Competitor(BaseModel):
    name: str
    url: str = ""
    pricing: str = ""
    positioning: str = ""


class MarketMap(BaseModel):
    """The structured output the agent produces and the node emits."""

    summary: str = ""
    competitors: list[Competitor] = Field(default_factory=list)
    top_keywords: list[str] = Field(default_factory=list)


def _build_prompt(inputs: Mapping[str, Any]) -> str:
    """Render gathered evidence into a single prompt for the SingleCallAgent."""
    thesis = inputs.get("thesis", "")
    keywords = inputs.get("keyword_volumes", [])
    search = inputs.get("search_results", [])
    lines = [
        "Synthesize a market landscape for this venture thesis.",
        f"Thesis: {thesis}",
        "Keyword volumes:",
        *[f"  - {k}" for k in keywords],
        "Competitor search results:",
        *[f"  - {s}" for s in search],
        "Return a structured MarketMap.",
    ]
    return "\n".join(lines)


class MarketScanner:
    name = "market-scanner"
    version = "0.1.0"
    kind = "agentic"
    reacts_to = ["research.requested"]
    # Descriptive metadata for introspection / visualization (Phase 1).
    emits = ["market.landscape.summarized"]
    calls = ["semrush-client", "web-search-client", "llm-gateway"]

    def __init__(
        self,
        *,
        semrush: SemrushClient | None = None,
        web_search: WebSearchClient | None = None,
        gateway: LLMGateway | None = None,
        agent: Agent | None = None,
    ) -> None:
        self._semrush = semrush or FakeSemrushClient()
        self._web_search = web_search or FakeWebSearchClient()
        # Node declares its own agent (default SingleCallAgent over fake gateway).
        self._agent = agent or SingleCallAgent(
            gateway or FakeLLMGateway(), _build_prompt
        )

    def handle(self, event: Event, ctx: NodeContext) -> None:
        thesis = event.payload.get("thesis", "")
        keywords = list(event.payload.get("keywords", []))
        competitors_query = event.payload.get(
            "competitor_query", f"{thesis} competitors"
        )

        # 1. Call library tools (leaf I/O) to gather evidence.
        volumes = self._semrush.keyword_volume(keywords) if keywords else []
        results = self._web_search.search(competitors_query)

        # 2. Hand the evidence to the agent for synthesis (one structured call).
        market_map, _completion = self._agent.run(
            {
                "thesis": thesis,
                "keyword_volumes": [v.model_dump() for v in volumes],
                "search_results": [r.model_dump() for r in results],
            },
            MarketMap,
        )

        # 3. Emit the structured landscape for anyone (thesis-tracker, Layer 3).
        ctx.emit(
            type="market.landscape.summarized",
            payload=market_map.model_dump(),
        )
