from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import typer
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.tasks import resolve_task
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
    assert "Dream: repo root" in first.output
    assert "Dream: using assignee claude1 (agent type claude, mode auto)" in first.output
    assert "Dream: scaffolding task 'Dream'" in first.output
    assert "Dream: created task dream at" in first.output
    assert "Dream: launch skipped (--no-launch)" in first.output
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


def test_dream_logs_before_launching(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(repo)
    calls: list[dict[str, object]] = []
    workers: list[dict[str, object]] = []

    def fake_workers(cfg, slug: str, task_path: Path, *, assignee: str) -> None:
        workers.append(
            {
                "repo_root": cfg.repo_root,
                "slug": slug,
                "task_path": task_path,
                "assignee": assignee,
            }
        )

    def fake_launch(
        task: str,
        title: str | None,
        agent_override: str | None,
        prompt_report: bool,
        force: bool,
    ) -> None:
        calls.append(
            {
                "task": task,
                "title": title,
                "agent_override": agent_override,
                "prompt_report": prompt_report,
                "force": force,
            }
        )
        typer.echo("fake launch called")

    monkeypatch.setattr("relay.commands.dream._run_deterministic_workers", fake_workers)
    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["dream", "--mode", "interactive"])

    assert result.exit_code == 0, result.output
    assert "Dream: repo root" in result.output
    assert "Dream: using assignee claude1 (agent type claude, mode interactive)" in result.output
    assert "Dream: scaffolding task 'Dream'" in result.output
    assert "Dream: created task dream at" in result.output
    assert "Dream: launching agent for dream" in result.output
    assert "fake launch called" in result.output
    assert workers == [
        {
            "repo_root": repo,
            "slug": "dream",
            "task_path": repo / "tasks" / "dream",
            "assignee": "claude1",
        }
    ]
    assert calls == [
        {
            "task": "dream",
            "title": None,
            "agent_override": None,
            "prompt_report": False,
            "force": False,
        }
    ]


def test_dream_worker_failure_skips_agent_launch(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(repo)
    launched: list[str] = []

    def fake_workers(cfg, slug: str, task_path: Path, *, assignee: str) -> None:
        raise SystemExit(2)

    def fake_launch(
        task: str,
        title: str | None,
        agent_override: str | None,
        prompt_report: bool,
        force: bool,
    ) -> None:
        launched.append(task)

    monkeypatch.setattr("relay.commands.dream._run_deterministic_workers", fake_workers)
    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["dream"])

    assert result.exit_code == 2
    assert launched == []


def test_dream_runs_deterministic_workers_before_agent_phase(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from relay.commands import dream as dream_cmd

    task_path = repo / "tasks" / "dream"
    task_path.mkdir(parents=True)
    (task_path / "blackboard.md").write_text("")
    cfg = load_config(repo)
    launched: list[str] = []
    bumped: list[tuple[str, str | None]] = []

    def fake_launch(
        task: str,
        title: str | None,
        agent_override: str | None,
        prompt_report: bool,
        force: bool,
    ) -> None:
        launched.append(task)
        ref = resolve_task(cfg, task)
        (ref.path / "blackboard.md").write_text(
            f"## Dream Worker: {task}\n\nResult: ok.\n"
        )

    def fake_bump(task: str, message: str | None = None) -> None:
        bumped.append((task, message))

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)
    monkeypatch.setattr("relay.commands.bump.bump", fake_bump)

    dream_cmd._run_deterministic_workers(cfg, "dream", task_path, assignee="claude1")

    assert launched == ["dream-validate-drift", "dream-cleanup-orphan-markers"]
    assert bumped == [
        ("dream-validate-drift", "parent Dream run: dream"),
        ("dream-cleanup-orphan-markers", "parent Dream run: dream"),
    ]

    validate_ticket = Ticket.read(
        repo / "tasks" / "dream-validate-drift" / "ticket.md"
    )
    cleanup_ticket = Ticket.read(
        repo / "tasks" / "dream-cleanup-orphan-markers" / "ticket.md"
    )
    assert validate_ticket.mode == "script"
    assert validate_ticket.workflow == {
        "name": "dream/script-worker",
        "steps": [{"name": "run", "skill": "bootstrap/dream/tasks/validate-drift"}],
    }
    assert cleanup_ticket.mode == "script"
    assert cleanup_ticket.workflow == {
        "name": "dream/script-worker",
        "steps": [
            {"name": "run", "skill": "bootstrap/dream/tasks/cleanup-orphan-markers"}
        ],
    }

    parent_blackboard = (task_path / "blackboard.md").read_text()
    assert "## Dream Child Worker: dream-validate-drift" in parent_blackboard
    assert "## Dream Child Worker: dream-cleanup-orphan-markers" in parent_blackboard
