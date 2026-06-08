"""``ad-analytics-collector`` — derived in PostlineAI Step 4.

> *The venture needs to: collect ad metrics on a schedule (impressions, CTR,
> CPC, CPL) and the landing page's signups.*

An **event-driven node** that reacts to ``campaign.launched``, pulls metrics
from the matching ads client plus landing-page signups from the analytics
client, and emits ``campaign.metrics.updated``.

- **Reacts to:** ``campaign.launched``. *(The walkthrough also lists a
  ``tick.daily`` timer trigger — deferred: there is no timer substrate yet, and
  the launch-triggered hop is enough to prove the decision loop. See TODO.)*
- **Calls:** ``linkedin-ads-client``, ``meta-ads-client``, ``analytics-client``.
- **Emits:** ``campaign.metrics.updated``.
- **Kind:** dumb (API stitching, no LLM).
"""

from __future__ import annotations

from flywheel.core.events import Event
from flywheel.core.node import NodeContext
from flywheel.libraries.ads_client import (
    AdsClient,
    FakeLinkedInAdsClient,
    FakeMetaAdsClient,
)
from flywheel.libraries.analytics_client import AnalyticsClient, FakeAnalyticsClient

# TODO(step6): also react to ``tick.daily`` once a timer substrate exists, so
# metrics refresh on a cadence rather than only at launch.


class AdAnalyticsCollector:
    name = "ad-analytics-collector"
    version = "0.1.0"
    kind = "dumb"
    reacts_to = ["campaign.launched"]
    emits = ["campaign.metrics.updated"]
    calls = ["linkedin-ads-client", "meta-ads-client", "analytics-client"]

    def __init__(
        self,
        *,
        clients: dict[str, AdsClient] | None = None,
        analytics: AnalyticsClient | None = None,
    ) -> None:
        self._clients: dict[str, AdsClient] = clients or {
            "linkedin": FakeLinkedInAdsClient(),
            "meta": FakeMetaAdsClient(),
        }
        self._analytics = analytics or FakeAnalyticsClient()

    def handle(self, event: Event, ctx: NodeContext) -> None:
        campaign_id = event.payload.get("campaign_id")
        platform = event.payload.get("platform", "linkedin")
        client = self._clients.get(platform)
        if client is None or not campaign_id:
            return

        metrics = client.get_metrics(campaign_id)
        landing = self._analytics.landing_stats(event.payload.get("landing_page", "/"))

        payload = metrics.model_dump()
        payload["signups"] = landing.signups
        payload["visitors"] = landing.visitors
        ctx.emit(type="campaign.metrics.updated", payload=payload)
