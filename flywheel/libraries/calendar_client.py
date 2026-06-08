"""``calendar-client`` — derived in PostlineAI Step 3.

A **library tool** (leaf I/O) wrapping a scheduling API (Calendly / Google
Calendar) used to book customer-discovery calls. Pure function calls; no events.

Fake-first per ``new_docs/stack.md``; the real httpx-backed impl swaps in behind
the ``CalendarClient`` Protocol when scheduling needs to hit a live provider.
PostlineAI Step 3 only needs the seam to exist so discovery calls can be booked;
the booking itself is trivially modelled here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CalendarEvent(BaseModel):
    event_id: str
    invitee: str
    starts_at: datetime


@runtime_checkable
class CalendarClient(Protocol):
    def schedule(self, invitee: str, starts_at: datetime | None = None) -> CalendarEvent: ...

    def list_events(self) -> list[CalendarEvent]: ...


class FakeCalendarClient:
    """Offline calendar client. Records bookings in memory, deterministically.

    Event ids are derived from the booking order so output is reproducible
    without a live provider.
    """

    def __init__(self) -> None:
        self._events: list[CalendarEvent] = []

    def schedule(self, invitee: str, starts_at: datetime | None = None) -> CalendarEvent:
        event = CalendarEvent(
            event_id=f"cal-{len(self._events) + 1}",
            invitee=invitee,
            starts_at=starts_at or _utcnow(),
        )
        self._events.append(event)
        return event

    def list_events(self) -> list[CalendarEvent]:
        return list(self._events)
