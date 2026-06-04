"""Shared test fixtures."""

import pytest


@pytest.fixture
def venture_id() -> str:
    """A test venture ID."""
    return "test-venture-001"


@pytest.fixture
def sample_messages() -> list[dict[str, str]]:
    """Sample LLM messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in exactly 3 words."},
    ]
