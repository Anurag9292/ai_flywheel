"""Tests for the guarded .env loader (flywheel.env)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import flywheel.env as env_mod
from flywheel.env import load_dotenv_if_present


def test_no_env_file_is_noop(monkeypatch: Any, tmp_path: Path) -> None:
    # Point the loader at a dir with no .env → returns False, raises nothing.
    monkeypatch.setattr(env_mod, "_REPO_ROOT", tmp_path)
    assert load_dotenv_if_present() is False


def test_loads_values_from_env_file(monkeypatch: Any, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("FLYWHEEL_TEST_VAR=from_dotenv\n", encoding="utf-8")
    monkeypatch.setattr(env_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.delenv("FLYWHEEL_TEST_VAR", raising=False)

    assert load_dotenv_if_present() is True
    assert os.environ["FLYWHEEL_TEST_VAR"] == "from_dotenv"


def test_does_not_override_existing_env(monkeypatch: Any, tmp_path: Path) -> None:
    # An already-set var (shell / debugger) must win over the .env file.
    (tmp_path / ".env").write_text("FLYWHEEL_TEST_VAR=from_dotenv\n", encoding="utf-8")
    monkeypatch.setattr(env_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setenv("FLYWHEEL_TEST_VAR", "from_shell")

    load_dotenv_if_present()
    assert os.environ["FLYWHEEL_TEST_VAR"] == "from_shell"


def test_repo_env_example_exists() -> None:
    # The committed template should exist and list the keys the code uses today.
    example = Path(env_mod._REPO_ROOT) / ".env.example"
    assert example.exists()
    text = example.read_text(encoding="utf-8")
    for key in ("FLYWHEEL_VENTURE", "OPENAI_API_KEY", "FIRECRAWL_API_KEY"):
        assert key in text
