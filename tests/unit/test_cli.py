"""Unit tests for the CLI tool."""

import json
import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "ai_flywheel.channels.cli", *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_health_command():
    """health command should return healthy status."""
    result = run_cli("health")
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["status"] == "healthy"
    assert "running" in output["message"].lower()


def test_venture_create_command():
    """venture create should report what it would do."""
    result = run_cli("venture", "create", "--name", "TestVenture", "--domain", "saas")
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["status"] == "ok"
    assert "TestVenture" in output["message"]
    assert "saas" in output["message"]


def test_agent_execute_command():
    """agent execute should report what it would do."""
    result = run_cli(
        "agent", "execute",
        "--agent-id", "agent-001",
        "--task", "write tests",
        "--venture-id", "ven-001",
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["status"] == "ok"
    assert "agent-001" in output["message"]
    assert "write tests" in output["message"]


def test_no_command_shows_help():
    """Running with no command should show help and exit 0."""
    result = run_cli()
    assert result.returncode == 0
    assert "AI Flywheel" in result.stdout or "usage" in result.stdout.lower()
