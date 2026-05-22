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
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


def test_launch_auto_mode_spawns_agent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auto mode launches: it spawns the agent with the configured `auto`
    args and flips the ticket to `in_progress`, like an interactive launch."""
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="Auto run", workflow_name=None,
        contexts=[], mode="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "auto-run"])
    assert result.exit_code == 0, result.output

    # Spawned `claude -p <composed-prompt>` — auto args from `[agents.claude]`.
    assert len(calls) == 1
    assert calls[0][0] == "claude"
    assert "-p" in calls[0]

    from relay.ticket import Ticket
    ticket = Ticket.read(repo / "tasks" / "auto-run" / "ticket.md")
    assert ticket.status == "in_progress"


def test_launch_mode_override_runs_auto_ticket_interactively(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay launch --mode interactive` runs a `mode: auto` ticket as an
    interactive session — and leaves the ticket file's `mode:` untouched."""
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="Auto run", workflow_name=None,
        contexts=[], mode="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run)
    monkeypatch.setattr("relay.commands.launch.shutil.which", lambda n: f"/usr/bin/{n}")
    # Interactive mode requires a TTY; the override path is no exception.
    monkeypatch.setattr(
        "relay.commands.launch._interactive_stdio_has_tty", lambda: True
    )

    runner = CliRunner()
    result = runner.invoke(app, ["launch", "auto-run", "--mode", "interactive"])
    assert result.exit_code == 0, result.output
    assert "mode overridden to 'interactive'" in result.output

    # Interactive spawn: `claude <prompt>` — no `-p` auto flag.
    assert len(calls) == 1
    assert calls[0][0] == "claude"
    assert "-p" not in calls[0]

    # The override is ephemeral — the ticket file still says `mode: auto`.
    from relay.ticket import Ticket
    ticket = Ticket.read(repo / "tasks" / "auto-run" / "ticket.md")
    assert ticket.mode == "auto"
    assert ticket.status == "in_progress"


def test_launch_mode_override_rejects_bad_value(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--mode` only accepts interactive / auto."""
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="Auto run", workflow_name=None,
        contexts=[], mode="auto", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    result = CliRunner().invoke(app, ["launch", "auto-run", "--mode", "script"])
    assert result.exit_code == 2
    assert "--mode must be 'interactive' or 'auto'" in result.output


def test_launch_mode_override_rejects_script_ticket(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `mode: script` ticket has no agent prompt — `--mode` can't override it."""
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="Script run", workflow_name=None,
        contexts=[], mode="script", owner="marc", assignee="claude",
        watchers=[], status="active",
    )

    result = CliRunner().invoke(
        app, ["launch", "script-run", "--mode", "interactive"]
    )
    assert result.exit_code == 2
    assert "not supported for script-mode tasks" in result.output