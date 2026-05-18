from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.scaffold import scaffold_task
from relay.config import load_config


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


def test_launch_auto_mode_is_temporarily_disabled(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auto mode is refused at launch time until streaming lands.

    `claude -p` and `codex exec` buffer stdout until completion, so auto
    launches produce no live console output. Until relay can stream the
    agent's structured output, launch refuses rather than letting runs
    sit silently. The check happens before any subprocess is spawned and
    before the status transitions to `in_progress`.
    """
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="Auto run", workflow_name=None,
        contexts=[], mode="auto", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )

    def fail_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("subprocess.run must not be called for auto-mode launches")

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fail_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "auto-run"])
    assert result.exit_code == 2, result.output
    assert "mode=auto is temporarily disabled" in result.output
    assert "mode: interactive" in result.output

    # Status must not have advanced to in_progress.
    from relay.ticket import Ticket
    ticket = Ticket.read(repo / "tasks" / "auto-run" / "ticket.md")
    assert ticket.status == "active"