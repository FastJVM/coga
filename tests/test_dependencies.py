from __future__ import annotations

from coga.dependencies import (
    DEPENDENCIES,
    agent_cli_missing_message,
    install_hint,
)


def test_install_hint_finds_manifest_entries() -> None:
    assert install_hint("claude") == "https://claude.com/claude-code"
    assert install_hint("codex") == "https://github.com/openai/codex"


def test_install_hint_returns_none_for_unlisted_binary() -> None:
    assert install_hint("some-custom-agent") is None


def test_agent_clis_are_not_required_at_init() -> None:
    """`claude`/`codex` live in the manifest for the point-of-need install
    hint, but a missing agent CLI must never block `coga init`."""
    by_name = {dep.name: dep for dep in DEPENDENCIES}
    assert not by_name["claude"].required_at_init
    assert not by_name["codex"].required_at_init


def test_agent_cli_missing_message_carries_install_hint() -> None:
    message = agent_cli_missing_message("claude")
    assert "Agent CLI 'claude' not found in PATH." in message
    assert "https://claude.com/claude-code" in message


def test_agent_cli_missing_message_without_hint_still_fails_loud() -> None:
    """An agent whose `cli` isn't in the manifest still gets the loud
    not-found error — just without an install URL."""
    message = agent_cli_missing_message("some-custom-agent")
    assert "Agent CLI 'some-custom-agent' not found in PATH." in message
    assert "http" not in message
