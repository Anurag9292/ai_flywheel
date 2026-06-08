"""``email-client`` — derived in PostlineAI Step 4.

A **library tool** (leaf I/O) wrapping a transactional email API (Postmark /
Resend) for founder notifications and, later, customer surveys. Pure function
calls; no events.

Fake-first per ``new_docs/stack.md``; the real impl swaps in behind the
``EmailClient`` Protocol when real email must be sent.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class EmailMessage(BaseModel):
    to: str
    subject: str
    body: str


@runtime_checkable
class EmailClient(Protocol):
    def send(self, to: str, subject: str, body: str) -> EmailMessage: ...


class FakeEmailClient:
    """Offline email client. Records sent messages in memory for inspection."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, to: str, subject: str, body: str) -> EmailMessage:
        msg = EmailMessage(to=to, subject=subject, body=body)
        self.sent.append(msg)
        return msg
