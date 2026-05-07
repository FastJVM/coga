from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    relay_os = tmp_path / "relay-os"
    relay_os.mkdir()
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(relay_os / "relay.local.toml", 'user = "marc"\n')
    return relay_os


def test_dream_no_launch_scaffolds_ad_hoc_task_without_time_bucket(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)

    runner = CliRunner()
    first = runner.invoke(app, ["dream", "--no-launch"])
    second = runner.invoke(app, ["dream", "--no-launch"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert "Created dream" in first.output
    assert "Created dream-2" in second.output
    assert (repo / "tasks" / "dream").is_dir()
    assert (repo / "tasks" / "dream-2").is_dir()
    assert not (repo / "tasks" / "dream-2026-W19").exists()

    ticket = Ticket.read(repo / "tasks" / "dream" / "ticket.md")
    assert ticket.title == "Dream"
    assert ticket.status == "draft"
    assert ticket.mode == "auto"
    assert ticket.assignee == "claude1"
    assert ticket.workflow is None
    assert "Run the Dream cleanup pass for this Relay repo." in ticket.body
