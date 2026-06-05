"""Multi-channel interaction — Slack, CLI, Web."""

from .slack import create_slack_app, run_slack_bot

__all__ = ["create_slack_app", "run_slack_bot"]
