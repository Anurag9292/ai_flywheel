"""Tests for core configuration."""

import os

import pytest


def test_settings_loads_defaults():
    """Settings should load with sensible defaults."""
    from ai_flywheel.core.config import Settings

    s = Settings(
        _env_file=None,  # Don't read .env in tests
        openai_api_key="test-key",
    )
    assert s.environment == "development"
    assert s.is_development is True
    assert s.is_production is False
    assert "flywheel" in s.database_url
    assert s.temporal_task_queue == "ai-flywheel-main"


def test_settings_production_mode():
    """Settings should detect production mode."""
    from ai_flywheel.core.config import Settings

    s = Settings(_env_file=None, environment="production")
    assert s.is_production is True
    assert s.is_development is False
