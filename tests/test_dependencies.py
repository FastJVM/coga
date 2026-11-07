from __future__ import annotations

import re
from pathlib import Path

from coga.dependencies import (
    AGENT_CLIS,
    DEPENDENCIES,
    agent_cli_missing_message,
)

SRC = Path(__file__).resolve().parent.parent / "src" / "coga"
_AGENT_WHICH = re.compile(r"shutil\.which\(\s*[\w.]*agent[\w.]*\.cli\s*\)")


def test_agent_clis_have_no_install_metadata() -> None:
    """Coga scans supported agent CLIs but never carries installer metadata."""
    dependency_names = {dep.name for dep in DEPENDENCIES}
    assert dependency_names.isdisjoint(AGENT_CLIS)


def test_agent_cli_missing_message_points_at_the_toml_not_path() -> None:
    """The one remedy is a `coga.toml` edit. `shutil.which` resolves a bare
    name or a full path, so `PATH` is not the requirement and must not be
    named as one."""
    message = agent_cli_missing_message("claude", "claude")
    assert "Agent CLI 'claude' not found." in message
    assert "[agents.claude]" in message
    assert "coga.toml" in message
    assert "PATH" not in message
    assert "http" not in message
    assert "install" not in message.lower()


def test_agent_cli_missing_message_names_the_table_not_the_binary() -> None:
    """A `cli` already set to a full path still points at the table that
    declared it, so the reader knows which line to change."""
    message = agent_cli_missing_message("claude", "/opt/homebrew/bin/claude")
    assert "Agent CLI '/opt/homebrew/bin/claude' not found." in message
    assert "[agents.claude]" in message
    assert "PATH" not in message


def test_custom_agent_cli_missing_message_still_fails_loud() -> None:
    """A repo-defined type names its own table, which need not match `cli`."""
    message = agent_cli_missing_message("house-agent", "some-custom-agent")
    assert "Agent CLI 'some-custom-agent' not found." in message
    assert "[agents.house-agent]" in message
    assert "http" not in message


def test_every_agent_cli_check_routes_through_the_shared_message() -> None:
    """`recurring_autofix` once rolled its own "is not on PATH" text for this
    exact failure, so the wording drifted from every other point of need and a
    PATH claim survived a sweep that fixed the others. Any module that checks a
    configured agent CLI must report it through the shared message."""
    checked, offenders = [], []
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if not _AGENT_WHICH.search(text):
            continue
        checked.append(str(path.relative_to(SRC)))
        if "agent_cli_missing_message" not in text:
            offenders.append(str(path.relative_to(SRC)))
    assert checked, "the agent-CLI presence check moved; update this guard"
    assert offenders == [], (
        "these modules check for a configured agent CLI but do not use "
        "`agent_cli_missing_message`, so their wording can drift: "
        + ", ".join(offenders)
    )
