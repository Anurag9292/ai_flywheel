from datetime import UTC, datetime

from flywheel.libraries.calendar_client import FakeCalendarClient
from flywheel.libraries.transcription_client import FakeTranscriptionClient


def test_fake_calendar_schedules_and_lists_deterministically() -> None:
    client = FakeCalendarClient()
    when = datetime(2026, 1, 1, tzinfo=UTC)
    first = client.schedule("founder@acme.com", when)
    second = client.schedule("founder@beta.com")
    assert first.event_id == "cal-1"
    assert second.event_id == "cal-2"
    assert first.starts_at == when
    assert [e.invitee for e in client.list_events()] == [
        "founder@acme.com",
        "founder@beta.com",
    ]


def test_fake_transcription_uses_fixture_then_generic() -> None:
    client = FakeTranscriptionClient(fixtures={"rec-1": "we hate writing posts"})
    assert client.transcribe("rec-1").text == "we hate writing posts"
    generic = client.transcribe("rec-unknown")
    assert generic.audio_ref == "rec-unknown"
    assert "rec-unknown" in generic.text
