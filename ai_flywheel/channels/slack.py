"""Slack integration — bot handlers for platform interaction.

This module defines the handler structure for Slack events.
In production, it would be connected to Slack's Events API via
a webhook endpoint in the FastAPI app.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from ai_flywheel.core.events import get_event_bus

logger = structlog.get_logger()

SlackHandler = Callable[[str, str, str], Coroutine[Any, Any, str]]


class SlackBot:
    """Slack bot that routes messages to platform modules."""

    def __init__(self):
        self._handlers: dict[str, SlackHandler] = {}
        self._event_bus = get_event_bus()
        self._register_handlers()

    def _register_handlers(self):
        """Register command handlers."""
        self._handlers = {
            "help": self._handle_help,
            "venture": self._handle_venture,
            "agent": self._handle_agent,
            "cost": self._handle_cost,
            "approve": self._handle_approve,
            "status": self._handle_status,
        }

    async def handle_message(
        self,
        text: str,
        user_id: str,
        channel_id: str,
        thread_ts: str | None = None,
    ) -> str:
        """Process an incoming Slack message and return a response."""
        parts = text.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        handler = self._handlers.get(command, self._handle_unknown)

        logger.info("slack_message_received", command=command, user=user_id, channel=channel_id)

        response = await handler(args, user_id, channel_id)

        await self._event_bus.publish(
            event_type="slack.message.handled",
            source_module="slack_bot",
            payload={"command": command, "user_id": user_id, "channel_id": channel_id},
        )

        return response

    async def _handle_help(self, args: str, user_id: str, channel_id: str) -> str:
        return (
            "*AI Flywheel Commands:*\n"
            "\u2022 `venture list` \u2014 List all ventures\n"
            "\u2022 `venture create <name> <domain>` \u2014 Create a venture\n"
            "\u2022 `agent list <venture_id>` \u2014 List agents\n"
            "\u2022 `agent run <agent_id> <task>` \u2014 Execute an agent\n"
            "\u2022 `cost <venture_id>` \u2014 Cost report\n"
            "\u2022 `approve <review_id>` \u2014 Approve a pending review\n"
            "\u2022 `status` \u2014 Platform health\n"
            "\u2022 `help` \u2014 Show this message"
        )

    async def _handle_venture(self, args: str, user_id: str, channel_id: str) -> str:
        parts = args.split()
        if not parts:
            return "Usage: `venture {list|create <name> <domain>}`"

        action = parts[0]
        if action == "list":
            return "\U0001f4cb *Ventures:* (would list from DB)"
        elif action == "create" and len(parts) >= 3:
            name, domain = parts[1], parts[2]
            return f"\u2705 Would create venture *{name}* in domain _{domain}_"
        return "Usage: `venture {list|create <name> <domain>}`"

    async def _handle_agent(self, args: str, user_id: str, channel_id: str) -> str:
        parts = args.split()
        if not parts:
            return "Usage: `agent {list <venture_id>|run <agent_id> <task>}`"

        action = parts[0]
        if action == "list" and len(parts) >= 2:
            return f"\U0001f916 *Agents for venture {parts[1]}:* (would list from DB)"
        elif action == "run" and len(parts) >= 3:
            agent_id = parts[1]
            task = " ".join(parts[2:])
            return f"\U0001f680 Would execute agent `{agent_id}` with task: _{task}_"
        return "Usage: `agent {list <venture_id>|run <agent_id> <task>}`"

    async def _handle_cost(self, args: str, user_id: str, channel_id: str) -> str:
        if not args.strip():
            return "Usage: `cost <venture_id>`"
        return f"\U0001f4b0 *Cost report for {args.strip()}:* (would query cost optimizer)"

    async def _handle_approve(self, args: str, user_id: str, channel_id: str) -> str:
        if not args.strip():
            return "Usage: `approve <review_id>`"
        review_id = args.strip()
        return f"\u2705 Would approve review `{review_id}` as user `{user_id}`"

    async def _handle_status(self, args: str, user_id: str, channel_id: str) -> str:
        return "\U0001f7e2 *AI Flywheel Status:* All systems operational"

    async def _handle_unknown(self, args: str, user_id: str, channel_id: str) -> str:
        return "\u2753 Unknown command. Type `help` for available commands."
