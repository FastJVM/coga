from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands.create import scaffold_task
from relay.config import load_config
from relay.tasks import list_tasks
from relay.ticket import Ticket


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
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "code.md",
        """
        ---
        name: code
        description: tiny.
        steps:
          - name: implement
          - name: pr
          - name: merge
        ---

        ## implement
        Write the code.
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(repo: Path, *, workflow: str | None = "code", status: str = "active") -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="Work", workflow_name=workflow,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status=status,
    )
    return ref["slug"], ref["path"]


# --- step ---------------------------------------------------------------------


def test_step_advances(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["step", "2", "--task", slug])
    assert result.exit_code == 0, result.output
    cfg = load_config(repo)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    assert t.step == "2 (pr)"
    assert "advanced to step 2" in (ref.path / "log.md").read_text()


def test_step_to_done_marks_done(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    # Workflow has 3 steps; step 4 = done
    runner.invoke(app, ["step", "2", "--task", slug])
    runner.invoke(app, ["step", "3", "--task", slug])
    result = runner.invoke(app, ["step", "4", "--task", slug])
    assert result.exit_code == 0
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "done"
    assert "task done" in (task_path / "log.md").read_text()


def test_step_rejects_non_active(repo: Path) -> None:
    slug, _ = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["step", "2", "--task", slug])
    assert result.exit_code == 2


def test_step_rejects_no_workflow(repo: Path) -> None:
    slug, _ = _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["step", "2", "--task", slug])
    assert result.exit_code == 2


# --- panic --------------------------------------------------------------------


def test_panic_writes_blocker_and_releases_lock(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    # Simulate a held lock
    from relay.lock import TaskLock
    TaskLock(task_path).acquire("claude1")
    runner = CliRunner()
    result = runner.invoke(app, ["panic", "--task", slug, "--reason", "unclear ceiling for 429 backoff"])
    # Panic exits non-zero so a parent process can detect agent distress.
    assert result.exit_code == 1, result.output
    blackboard = (task_path / "blackboard.md").read_text()
    assert "unclear ceiling for 429 backoff" in blackboard
    assert "## Blockers" in blackboard
    assert not TaskLock(task_path).path.exists()
    assert "panic:" in (task_path / "log.md").read_text()


# --- feed ---------------------------------------------------------------------


def test_feed_logs(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["feed", "--task", slug, "--message", "opened PR #142"])
    assert result.exit_code == 0
    assert "feed: opened PR #142" in (task_path / "log.md").read_text()


# --- status -------------------------------------------------------------------


def test_status_shows_active(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert slug in result.output


def test_status_hides_done_by_default(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None)
    # Mark done directly
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["status"] = "done"
    t.write(task_path / "ticket.md")
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert "(no tasks)" in result.output
    result_all = runner.invoke(app, ["status", "--all"])
    assert slug in result_all.output
