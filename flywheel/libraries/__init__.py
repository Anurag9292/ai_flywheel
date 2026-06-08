"""Layer 1 **library tools** — the hands.

Plain functions/clients you import and call directly. *No events, no
subscriptions* (``new_docs/README.md`` §"Layer 1"). A node calls one or more of
these inside its handler to get work done.

Every library is defined as a ``Protocol`` (the interface) with a ``Fake``
implementation that runs offline. This is the fake/real seam from
``new_docs/stack.md``: program against the interface, ship a thin first impl,
swap the real one (litellm, httpx clients) in behind the same Protocol when a
venture step genuinely needs live I/O.
"""

from flywheel.libraries.ads_client import (
    AdsClient,
    CampaignMetrics,
    FakeLinkedInAdsClient,
    FakeMetaAdsClient,
    LaunchedCampaign,
)
from flywheel.libraries.analytics_client import (
    AnalyticsClient,
    FakeAnalyticsClient,
    LandingStats,
)
from flywheel.libraries.calendar_client import (
    CalendarClient,
    CalendarEvent,
    FakeCalendarClient,
)
from flywheel.libraries.email_client import (
    EmailClient,
    EmailMessage,
    FakeEmailClient,
)
from flywheel.libraries.llm_gateway import FakeLLMGateway, LLMGateway
from flywheel.libraries.semrush_client import (
    FakeSemrushClient,
    KeywordVolume,
    SemrushClient,
)
from flywheel.libraries.slack_client import (
    FakeSlackClient,
    SlackClient,
    SlackMessage,
)
from flywheel.libraries.transcription_client import (
    FakeTranscriptionClient,
    Transcript,
    TranscriptionClient,
)
from flywheel.libraries.web_search_client import (
    FakeWebSearchClient,
    SearchResult,
    WebSearchClient,
)

__all__ = [
    "LLMGateway",
    "FakeLLMGateway",
    "WebSearchClient",
    "FakeWebSearchClient",
    "SearchResult",
    "SemrushClient",
    "FakeSemrushClient",
    "KeywordVolume",
    "CalendarClient",
    "FakeCalendarClient",
    "CalendarEvent",
    "TranscriptionClient",
    "FakeTranscriptionClient",
    "Transcript",
    "AdsClient",
    "FakeLinkedInAdsClient",
    "FakeMetaAdsClient",
    "LaunchedCampaign",
    "CampaignMetrics",
    "AnalyticsClient",
    "FakeAnalyticsClient",
    "LandingStats",
    "SlackClient",
    "FakeSlackClient",
    "SlackMessage",
    "EmailClient",
    "FakeEmailClient",
    "EmailMessage",
]
