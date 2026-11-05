from __future__ import annotations

from coga.dependencies import (
    AGENT_CLIS,
    DEPENDENCIES,
    agent_cli_missing_message,
)


def test_agent_clis_have_no_install_metadata() -> None:
    """Coga scans supported agent CLIs but never carries installer metadata."""
    dependency_names = {dep.name for dep in DEPENDENCIES}
    assert dependency_names.isdisjoint(AGENT_CLIS)


def test_agent_cli_missing_message_names_only_the_path_requirement() -> None:
    message = agent_cli_missing_message("claude")
    assert "Agent CLI 'claude' not found in PATH." in message
    assert "requires the configured agent CLI on PATH" in message
    assert "http" not in message
    assert "install" not in message.lower()


def test_custom_agent_cli_missing_message_still_fails_loud() -> None:
    message = agent_cli_missing_message("some-custom-agent")
    assert "Agent CLI 'some-custom-agent' not found in PATH." in message
    assert "http" not in message
