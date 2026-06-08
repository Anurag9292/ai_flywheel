"""``slack-client`` — derived in PostlineAI Step 4.

A **library tool** (leaf I/O) wrapping the Slack web API for one-way founder
notifications. Pure function calls; no events.

Fake-first per ``new_docs/stack.md``; the real impl swaps in behind the
``SlackClient`` Protocol when notifications must reach a real workspace. Two-way
Slack (slash commands / interactive approvals via Bolt) is deferred to ~Step 5.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class SlackMessage(BaseModel):
    channel: str
    text: str


@runtime_checkable
class SlackClient(Protocol):
    def post_message(self, channel: str, text: str) -> SlackMessage: ...


class FakeSlackClient:
    """Offline Slack client. Records posted messages in memory for inspection."""

    def __init__(self) -> None:
        self.sent: list[SlackMessage] = []

    def post_message(self, channel: str, text: str) -> SlackMessage:
        msg = SlackMessage(channel=channel, text=text)
        self.sent.append(msg)
        return msg
