"""Unit tests for the Slack integration bot."""

from unittest.mock import AsyncMock, patch

import pytest

from ai_flywheel.channels.slack import SlackBot


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def bot(mock_event_bus):
    """Create a SlackBot instance with mocked event bus."""
    with patch("ai_flywheel.channels.slack.get_event_bus", return_value=mock_event_bus):
        return SlackBot()


async def test_handle_help(bot, mock_event_bus):
    """help command should return the commands list."""
    with patch("ai_flywheel.channels.slack.get_event_bus", return_value=mock_event_bus):
        response = await bot.handle_message("help", "U001", "C001")

    assert "*AI Flywheel Commands:*" in response
    assert "venture list" in response
    assert "approve" in response


async def test_handle_venture_list(bot, mock_event_bus):
    """venture list command should return venture listing."""
    with patch("ai_flywheel.channels.slack.get_event_bus", return_value=mock_event_bus):
        response = await bot.handle_message("venture list", "U001", "C001")

    assert "Ventures" in response


async def test_handle_approve(bot, mock_event_bus):
    """approve command should acknowledge the review ID."""
    with patch("ai_flywheel.channels.slack.get_event_bus", return_value=mock_event_bus):
        response = await bot.handle_message("approve review-123", "U001", "C001")

    assert "review-123" in response
    assert "U001" in response


async def test_handle_status(bot, mock_event_bus):
    """status command should return operational status."""
    with patch("ai_flywheel.channels.slack.get_event_bus", return_value=mock_event_bus):
        response = await bot.handle_message("status", "U001", "C001")

    assert "operational" in response.lower() or "Status" in response


async def test_handle_unknown(bot, mock_event_bus):
    """unknown commands should return an error message."""
    with patch("ai_flywheel.channels.slack.get_event_bus", return_value=mock_event_bus):
        response = await bot.handle_message("foobar", "U001", "C001")

    assert "Unknown command" in response or "unknown" in response.lower()
