from flywheel.core.events import Event, InMemoryEventBus
from flywheel.core.node import Runtime
from flywheel.core.substrate import TraceRecorder
from flywheel.libraries.ads_client import (
    CampaignMetrics,
    FakeLinkedInAdsClient,
    FakeMetaAdsClient,
)
from flywheel.libraries.analytics_client import FakeAnalyticsClient, LandingStats
from flywheel.nodes.ad_analytics_collector import AdAnalyticsCollector
from flywheel.nodes.ad_campaign_runner import AdCampaignRunner


def _runtime(tmp_path, *nodes):
    bus = InMemoryEventBus()
    recorder = TraceRecorder(bus, log_path=tmp_path / "t.jsonl")
    runtime = Runtime(bus, recorder)
    for node in nodes:
        runtime.register(node)
    return bus, runtime


# --- library fakes -----------------------------------------------------------


def test_fake_ads_clients_are_deterministic_and_platform_tagged() -> None:
    li = FakeLinkedInAdsClient()
    launched = li.launch_campaign("ghostwriting waitlist", 200.0)
    assert launched.platform == "linkedin"
    assert launched.campaign_id == "linkedin-camp-1"
    m1 = li.get_metrics(launched.campaign_id)
    m2 = li.get_metrics(launched.campaign_id)
    assert m1 == m2  # deterministic

    meta = FakeMetaAdsClient()
    assert meta.launch_campaign("x", 50.0).platform == "meta"


def test_fake_analytics_fixture_then_pseudo() -> None:
    client = FakeAnalyticsClient(
        fixtures={"/lp": LandingStats(page="/lp", visitors=1000, signups=80)}
    )
    assert client.landing_stats("/lp").signups == 80
    generic = client.landing_stats("/other")
    assert generic.page == "/other"


# --- ad-campaign-runner ------------------------------------------------------


def test_campaign_runner_launches_on_selected_platform(tmp_path) -> None:
    runner = AdCampaignRunner()
    bus, _ = _runtime(tmp_path, runner)
    out: list[Event] = []
    bus.subscribe("campaign.launched", out.append)

    bus.publish(Event(
        type="campaign.requested",
        venture_id="postlineai",
        payload={"platform": "meta", "name": "waitlist", "budget_usd": 200},
    ))

    assert len(out) == 1
    assert out[0].payload["platform"] == "meta"
    assert out[0].payload["budget_usd"] == 200.0


def test_campaign_runner_ignores_unknown_platform(tmp_path) -> None:
    runner = AdCampaignRunner()
    bus, _ = _runtime(tmp_path, runner)
    out: list[Event] = []
    bus.subscribe("campaign.launched", out.append)

    bus.publish(Event(
        type="campaign.requested",
        venture_id="v",
        payload={"platform": "tiktok"},
    ))
    assert out == []


# --- ad-analytics-collector --------------------------------------------------


def test_analytics_collector_emits_metrics_with_signups(tmp_path) -> None:
    collector = AdAnalyticsCollector(
        clients={
            "linkedin": FakeLinkedInAdsClient(
                metrics={
                    "linkedin-camp-1": CampaignMetrics(
                        campaign_id="linkedin-camp-1", platform="linkedin",
                        impressions=10000, clicks=200, leads=40, spend_usd=200.0,
                    )
                }
            )
        },
        analytics=FakeAnalyticsClient(
            fixtures={"/lp": LandingStats(page="/lp", visitors=200, signups=18)}
        ),
    )
    bus, _ = _runtime(tmp_path, collector)
    out: list[Event] = []
    bus.subscribe("campaign.metrics.updated", out.append)

    bus.publish(Event(
        type="campaign.launched",
        venture_id="postlineai",
        payload={"campaign_id": "linkedin-camp-1", "platform": "linkedin",
                 "landing_page": "/lp"},
    ))

    assert len(out) == 1
    assert out[0].payload["leads"] == 40
    assert out[0].payload["signups"] == 18


def test_runner_then_collector_chain(tmp_path) -> None:
    """campaign.requested -> launched -> metrics.updated, in one bus."""
    bus, _ = _runtime(tmp_path, AdCampaignRunner(), AdAnalyticsCollector())
    metrics: list[Event] = []
    bus.subscribe("campaign.metrics.updated", metrics.append)

    bus.publish(Event(
        type="campaign.requested",
        venture_id="postlineai",
        payload={"platform": "linkedin", "name": "wl", "budget_usd": 200},
    ))

    assert len(metrics) == 1
    assert metrics[0].payload["platform"] == "linkedin"
