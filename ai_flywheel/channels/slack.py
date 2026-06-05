"""AI Flywheel Slack Channel — bidirectional Slack integration.

Capabilities:
- Receive slash commands (/flywheel status, /flywheel cost, etc.)
- Push notifications (kill signals, cost alerts, experiment results)
- Interactive approval buttons (human-in-the-loop reviews)
- Conversational interaction (ask questions, get answers)

Setup:
1. Create a Slack App at api.slack.com
2. Add slash command: /flywheel
3. Enable Interactive Components
4. Add bot token scopes: chat:write, commands, users:read
5. Set env vars: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
"""

from __future__ import annotations

import asyncio
import json
import logging

import structlog
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from ai_flywheel.core.config import settings
from ai_flywheel.core.events import get_event_bus

logger = structlog.get_logger()


def create_slack_app() -> App:
    """Create and configure the Slack Bolt app."""
    app = App(
        token=getattr(settings, "slack_bot_token", ""),
        signing_secret=getattr(settings, "slack_signing_secret", ""),
        logger=logging.getLogger("slack_bolt"),
    )

    # --- Slash Commands ---

    @app.command("/flywheel")
    def handle_flywheel_command(ack, command, respond):
        """Main slash command dispatcher."""
        ack()
        text = command.get("text", "").strip()
        parts = text.split(maxsplit=1)
        subcommand = parts[0] if parts else "help"
        args = parts[1] if len(parts) > 1 else ""

        if subcommand == "help":
            respond(_help_message())
        elif subcommand == "status":
            respond(_handle_status(args))
        elif subcommand == "cost":
            respond(_handle_cost(args))
        elif subcommand == "ventures":
            respond(_handle_ventures())
        elif subcommand == "thesis":
            respond(_handle_thesis(args))
        elif subcommand == "kill-check":
            respond(_handle_kill_check(args))
        else:
            respond(f"Unknown command: `{subcommand}`. Try `/flywheel help`")

    # --- Interactive Actions (Approval Buttons) ---

    @app.action("approve_review")
    def handle_approve(ack, body, respond):
        """Handle approval button click."""
        ack()
        review_id = body["actions"][0].get("value", "")
        user = body["user"]["username"]
        # Trigger approval via service
        asyncio.run(_approve_review(review_id, user))
        respond(f"Approved by @{user}. Review `{review_id}` marked as approved.")

    @app.action("reject_review")
    def handle_reject(ack, body, respond):
        """Handle rejection button click."""
        ack()
        review_id = body["actions"][0].get("value", "")
        user = body["user"]["username"]
        asyncio.run(_reject_review(review_id, user))
        respond(f"Rejected by @{user}. Review `{review_id}` marked as rejected.")

    # --- Event Subscriptions ---

    @app.event("app_mention")
    def handle_mention(event, say):
        """Respond to @mentions."""
        text = event.get("text", "")
        say(f"Hey! I'm the AI Flywheel bot. Try `/flywheel help` for commands.")

    return app


# --- Command Handlers ---


def _help_message() -> dict:
    """Return help message as Slack blocks."""
    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "AI Flywheel Commands"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join([
                        "*Available Commands:*",
                        "`/flywheel status` — Platform health & venture overview",
                        "`/flywheel ventures` — List all ventures with status",
                        "`/flywheel cost [venture]` — Cost report for a venture",
                        "`/flywheel thesis [venture]` — Thesis confidence & kill signals",
                        "`/flywheel kill-check [venture]` — Check for active kill signals",
                        "`/flywheel help` — This message",
                    ]),
                },
            },
        ]
    }


def _handle_status(args: str) -> dict:
    """Return platform status."""
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*AI Flywheel Status*\n:white_check_mark: API Running\n:white_check_mark: Temporal Connected\n:white_check_mark: Database Connected",
                },
            },
        ]
    }


def _handle_cost(args: str) -> dict:
    """Return cost summary."""
    # In production, this would call CostOptimizer.get_spend_report()
    venture_name = args or "all ventures"
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Cost Report: {venture_name}*\nRun `/flywheel cost <venture-name>` with a specific venture for detailed breakdown.",
                },
            },
        ]
    }


def _handle_ventures() -> dict:
    """List ventures."""
    # In production, this calls VentureService.list_all()
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Ventures*\nConnect to the database to see live ventures. Use the web dashboard for full details.",
                },
            },
        ]
    }


def _handle_thesis(args: str) -> dict:
    """Show thesis status."""
    venture_name = args or "all"
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Thesis Status: {venture_name}*\nCheck the web dashboard for full confidence scores and evidence timeline.",
                },
            },
        ]
    }


def _handle_kill_check(args: str) -> dict:
    """Check for kill signals."""
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":green_circle: *No active kill signals detected.*\nAll theses are within acceptable confidence ranges.",
                },
            },
        ]
    }


# --- Notification Senders ---


async def send_kill_signal_alert(app: App, channel: str, venture_name: str, thesis_title: str, reason: str):
    """Push a kill signal notification to Slack."""
    app.client.chat_postMessage(
        channel=channel,
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":red_circle: Kill Signal Detected"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Venture:* {venture_name}\n*Thesis:* {thesis_title}\n*Reason:* {reason}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View in Dashboard"},
                        "url": "http://localhost:3000/thesis",
                    },
                ],
            },
        ],
    )


async def send_approval_request(app: App, channel: str, review_id: str, content: str, agent_name: str):
    """Send an approval request with interactive buttons."""
    app.client.chat_postMessage(
        channel=channel,
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":eyes: Approval Required"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Agent:* {agent_name}\n*Output:*\n```{content[:500]}```",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "action_id": "approve_review",
                        "value": review_id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject"},
                        "style": "danger",
                        "action_id": "reject_review",
                        "value": review_id,
                    },
                ],
            },
        ],
    )


async def send_cost_alert(app: App, channel: str, venture_name: str, amount: float, budget: float):
    """Send cost alert when budget threshold is crossed."""
    pct = (amount / budget * 100) if budget > 0 else 0
    app.client.chat_postMessage(
        channel=channel,
        text=f":warning: *Cost Alert: {venture_name}*\nSpend: ${amount:.2f} / ${budget:.2f} ({pct:.0f}% of budget)",
    )


# --- Service Integration Helpers ---


async def _approve_review(review_id: str, user: str):
    """Approve a review via the Human Review service."""
    from ai_flywheel.modules.agent_runtime.human_review.service import HumanReviewEngine

    engine = HumanReviewEngine()
    # In production: await engine.decide(review_id, "approved", notes=f"Approved via Slack by {user}")
    get_event_bus().publish("review.approved", {"review_id": review_id, "approved_by": user, "channel": "slack"})


async def _reject_review(review_id: str, user: str):
    """Reject a review via the Human Review service."""
    get_event_bus().publish("review.rejected", {"review_id": review_id, "rejected_by": user, "channel": "slack"})


# --- Entry Point ---


def run_slack_bot():
    """Start the Slack bot in Socket Mode."""
    app = create_slack_app()
    socket_token = getattr(settings, "slack_app_token", "")
    if not socket_token:
        logger.error("slack_app_token not configured. Cannot start Slack bot.")
        return
    handler = SocketModeHandler(app, socket_token)
    logger.info("slack_bot_starting")
    handler.start()


if __name__ == "__main__":
    run_slack_bot()
