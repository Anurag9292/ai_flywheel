"""``linkedin-ads-client`` / ``meta-ads-client`` — derived in PostlineAI Step 4.

**Library tools** (leaf I/O) wrapping ad-platform marketing APIs. Both platforms
satisfy the *same* ``AdsClient`` Protocol — that is deliberate: the
``ad-campaign-runner`` and ``ad-analytics-collector`` nodes route to whichever
platform a campaign targets without caring which concrete client backs it.

Pure function calls; no events. Fake-first per ``new_docs/stack.md``; real
httpx-backed impls (LinkedIn Marketing API, Meta Marketing API) swap in behind
the Protocol when a live ad test runs.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class LaunchedCampaign(BaseModel):
    campaign_id: str
    platform: str
    budget_usd: float


class CampaignMetrics(BaseModel):
    campaign_id: str
    platform: str
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    spend_usd: float = 0.0


@runtime_checkable
class AdsClient(Protocol):
    platform: str

    def launch_campaign(
        self, name: str, budget_usd: float, targeting: dict[str, object] | None = None
    ) -> LaunchedCampaign: ...

    def get_metrics(self, campaign_id: str) -> CampaignMetrics: ...


class _FakeAdsClient:
    """Offline ads client returning deterministic launches + metrics.

    Metrics are derived from a stable hash of the campaign id so a given
    campaign always reports the same numbers — reproducible without a provider.
    Concrete platforms subclass this and set ``platform``.
    """

    platform = "fake"

    def __init__(self, metrics: dict[str, CampaignMetrics] | None = None) -> None:
        self._metrics = metrics or {}
        self._launched = 0

    def launch_campaign(
        self, name: str, budget_usd: float, targeting: dict[str, object] | None = None
    ) -> LaunchedCampaign:
        self._launched += 1
        return LaunchedCampaign(
            campaign_id=f"{self.platform}-camp-{self._launched}",
            platform=self.platform,
            budget_usd=budget_usd,
        )

    def get_metrics(self, campaign_id: str) -> CampaignMetrics:
        if campaign_id in self._metrics:
            return self._metrics[campaign_id]
        seed = sum(ord(c) for c in campaign_id)
        impressions = (seed * 53) % 20_000
        clicks = impressions // 50
        return CampaignMetrics(
            campaign_id=campaign_id,
            platform=self.platform,
            impressions=impressions,
            clicks=clicks,
            leads=clicks // 5,
            spend_usd=round((seed % 200) + 0.0, 2),
        )


class FakeLinkedInAdsClient(_FakeAdsClient):
    platform = "linkedin"


class FakeMetaAdsClient(_FakeAdsClient):
    platform = "meta"
