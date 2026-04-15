"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """An empty Relay-like repo with just a minimal `relay.toml`."""
    (tmp_path / "relay.toml").write_text("version = 1\n")
    return tmp_path


# -- Spec-example configs ------------------------------------------------
#
# These mirror the TOML blocks in the consolidated spec so tests that
# assert on realistic shapes (rather than synthetic minimal ones) have
# one source of truth. Individual tests override or extend as needed.


SPEC_RELAY_TOML = dedent(
    """\
    version = 1

    [projects.email-tool]
    type = "repo"
    remote = "git@github.com:company/email-tool.git"
    default_status = "ready"

    [projects.content]
    type = "local"
    default_status = "ready"

    [projects.ops]
    type = "local"
    default_status = "design"

    [agents.claude]
    cli = "claude"
    interactive = "--append-system-prompt-file"
    auto = "-p"
    file = "CLAUDE.md"
    mode = "local"

    [agents.codex]
    cli = "codex"
    interactive = "exec"
    auto = "exec"
    file = "AGENTS.md"
    mode = "local"

    [assignees.marc]
    agents = { "claude1" = "claude", "claude2" = "claude" }
    slack = "U04ABCDEF"

    [assignees.pierre]
    agents = { "claude2" = "claude" }
    slack = "U04GHIJKL"

    [slack]
    """
)


SPEC_LOCAL_TOML = dedent(
    """\
    user = "marc"

    [paths]
    email-tool = "./email-tool"
    content = "./content"
    ops = "./ops"

    [secrets]
    """
)


@pytest.fixture
def spec_repo(tmp_path: Path) -> Path:
    """A repo with the full spec-example `relay.toml` and a matching
    `relay.local.toml`. No secrets set by default."""
    (tmp_path / "relay.toml").write_text(SPEC_RELAY_TOML)
    (tmp_path / "relay.local.toml").write_text(SPEC_LOCAL_TOML)
    return tmp_path
