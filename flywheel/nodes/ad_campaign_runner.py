"""``ad-campaign-runner`` — derived in PostlineAI Step 4.

> *The venture needs to: launch and configure ad campaigns on LinkedIn and
> Facebook with copy + creative + targeting.*

An **event-driven node** that reacts to ``campaign.requested``, calls the
appropriate ads client (selected by the request's ``platform``), and emits
``campaign.launched``.

- **Reacts to:** ``campaign.requested``.
- **Calls:** ``linkedin-ads-client``, ``meta-ads-client``.
- **Emits:** ``campaign.launched``.
- **Kind:** dumb (API stitching, no LLM).

The node holds one ``AdsClient`` per platform behind the shared Protocol, so the
same node serves every platform — adding a third is a one-line registration.
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.ads_client import (
    AdsClient,
    FakeLinkedInAdsClient,
    FakeMetaAdsClient,
)


class AdCampaignRunner:
    name = "ad-campaign-runner"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["campaign.requested"]
    emits = ["campaign.launched"]
    calls = ["linkedin-ads-client", "meta-ads-client"]

    def __init__(self, *, clients: dict[str, AdsClient] | None = None) -> None:
        self._clients: dict[str, AdsClient] = clients or {
            "linkedin": FakeLinkedInAdsClient(),
            "meta": FakeMetaAdsClient(),
        }

    def handle(self, event: Event, ctx: NodeContext) -> None:
        platform = event.payload.get("platform", "linkedin")
        client = self._clients.get(platform)
        if client is None:
            # Unknown platform: a dumb node simply does nothing.
            return

        name = event.payload.get("name", "untitled campaign")
        budget = float(event.payload.get("budget_usd", 0.0))
        targeting = event.payload.get("targeting")

        launched = client.launch_campaign(name, budget, targeting)
        ctx.emit(type="campaign.launched", payload=launched.model_dump())
