from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
import typer
from typer.testing import CliRunner

from relay.cli import app
from relay.ticket import Ticket

from conftest import seed_direct_body_workflow


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
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        """,
    )
    _write(
        relay_os / "relay.local.toml",
        """
        user = "marc"
        [slack]
        enabled = false
        """,
    )
    # Retire creates its task with the `direct/body` workflow; the minimal
    # test repo needs that shipped workflow + skill present (real repos get it
    # from `relay init`) or `create_task` fails to load the workflow.
    seed_direct_body_workflow(relay_os)
    return relay_os


def _seed_done_task(repo: Path, slug: str = "fix-retry-logic") -> Path:
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        f"""
        ---
        slug: {slug}
        title: Fix retry logic
        status: done
        autonomy: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Done.
        """,
    )
    (task_dir / "blackboard.md").write_text("# Fix retry logic\n")
    (task_dir / "log.md").write_text("")
    return task_dir


def test_retire_no_launch_creates_task_with_target_slug(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "fix-retry-logic")

    result = CliRunner().invoke(app, ["retire", "fix-retry-logic", "--no-launch"])

    assert result.exit_code == 0, result.output
    assert "Retire: target task fix-retry-logic" in result.output
    assert "Retire: using assignee claude (agent type claude, autonomy interactive)" in result.output
    assert "Retire: creating task 'Retire fix-retry-logic'" in result.output
    assert "Retire: created task retire-fix-retry-logic" in result.output
    assert "Retire: launch skipped (--no-launch)" in result.output
    assert "relay launch retire-fix-retry-logic" in result.output

    new_task = repo / "tasks" / "retire-fix-retry-logic.md"
    assert new_task.is_file()
    ticket = Ticket.read(new_task)
    assert ticket.title == "Retire fix-retry-logic"
    # Retire tasks create straight to `active`, carrying the `direct/body`
    # workflow so they run their body directly while still being a
    # workflow-carrying, bumpable, valid active task.
    assert ticket.status == "active"
    assert ticket.autonomy == "interactive"
    assert ticket.assignee == "claude"
    assert ticket.workflow["name"] == "direct/body"
    assert "Retire the done ticket `fix-retry-logic`" in ticket.body
    assert "retro/done-ticket" in ticket.body
    # Source task untouched until the agent runs the retro skill.
    assert (repo / "tasks" / "fix-retry-logic" / "ticket.md").is_file()


def test_retire_refuses_non_done_target(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    task_dir = repo / "tasks" / "in-flight"
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        """
        ---
        slug: in-flight
        title: Still going
        status: active
        autonomy: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Active.
        """,
    )
    (task_dir / "blackboard.md").write_text("")
    (task_dir / "log.md").write_text("")

    result = CliRunner().invoke(app, ["retire", "in-flight", "--no-launch"])

    assert result.exit_code == 2
    assert "Retire only operates on done tickets" in result.output
    assert "is 'active'" in result.output
    # Refused — no retire create task created.
    assert not (repo / "tasks" / "retire-in-flight").exists()


def test_retire_refuses_unknown_slug(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "real-task")

    result = CliRunner().invoke(app, ["retire", "no-such-task", "--no-launch"])

    assert result.exit_code == 2
    assert "no-such-task" in result.output


def test_retire_refuses_auto_mode(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay retire <slug> --autonomy auto` is rejected while auto is disabled."""
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "fix-retry-logic")

    result = CliRunner().invoke(
        app, ["retire", "fix-retry-logic", "--autonomy", "auto", "--no-launch"]
    )

    assert result.exit_code == 2
    assert "autonomy=auto is temporarily disabled" in result.output
    assert not (repo / "tasks" / "retire-fix-retry-logic").exists()


def test_retire_launches_after_create(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "fix-retry-logic")
    calls: list[dict[str, object]] = []

    def fake_launch(
        task: str,
        agent_override: str | None,
        prompt_report: bool,
        autonomy_override: str | None = None,
    ) -> None:
        ticket = Ticket.read(repo / "tasks" / f"{task}.md")
        assert ticket.status == "active"
        calls.append(
            {
                "task": task,
                "agent_override": agent_override,
                "prompt_report": prompt_report,
                "autonomy_override": autonomy_override,
            }
        )
        typer.echo("fake launch called")

    monkeypatch.setattr("relay.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(
        app, ["retire", "fix-retry-logic", "--autonomy", "interactive"]
    )

    assert result.exit_code == 0, result.output
    assert "Retire: created task retire-fix-retry-logic" in result.output
    assert "(active)" in result.output
    assert "Retire: launching retire-fix-retry-logic" in result.output
    assert "fake launch called" in result.output
    # The audit log is the repo-global `relay-os/log.md` now; filter it to the
    # retire task's ref instead of reading a per-task log.md (which is gone).
    from relay.config import load_config
    from relay.logfile import task_log_lines

    cfg = load_config(repo)
    log = "\n".join(task_log_lines(cfg, "retire-fix-retry-logic"))
    assert "created (autonomy=interactive, status=active)" in log
    assert calls == [
        {
            "task": "retire-fix-retry-logic",
            "agent_override": None,
            "prompt_report": False,
            "autonomy_override": None,
        }
    ]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc


def test_retire_prunes_merged_branch_before_launch(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """retire deletes the ticket's branch (read from `## Dev`) before launching.

    The branch was merged into `main` (an ancestor of HEAD), so the local
    `git branch -d` path applies — no `gh`/origin needed; the remote delete
    self-skips without a merged-PR signal.
    """
    monkeypatch.chdir(repo)
    _git(repo, "init", "-b", "main", ".")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Tester")
    (repo / "seed.txt").write_text("seed")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-m", "seed")
    # A feature branch whose commit lands in main (fast-forward) — merged.
    _git(repo, "checkout", "-b", "fix-retry-branch")
    (repo / "work.txt").write_text("work")
    _git(repo, "add", "work.txt")
    _git(repo, "commit", "-m", "work")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--ff-only", "fix-retry-branch")

    slug = "fix-retry-logic"
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        f"""
        ---
        slug: {slug}
        title: Fix retry logic
        status: done
        autonomy: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Done.

        <!-- relay:blackboard -->

        ## Dev
        branch: fix-retry-branch
        pr: https://github.com/owner/repo/pull/9
        """,
    )
    (task_dir / "log.md").write_text("")

    assert (
        subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
             "refs/heads/fix-retry-branch"],
            capture_output=True,
        ).returncode
        == 0
    )

    result = CliRunner().invoke(app, ["retire", slug, "--no-launch"])

    assert result.exit_code == 0, result.output
    assert "Branch cleanup: deleted local 'fix-retry-branch'." in result.output
    # Branch is gone, and it happened before the retro task even existed.
    assert (
        subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
             "refs/heads/fix-retry-branch"],
            capture_output=True,
        ).returncode
        != 0
    )


def test_retire_resolves_unique_prefix(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_done_task(repo, "fix-retry-logic")

    result = CliRunner().invoke(app, ["retire", "fix-retr", "--no-launch"])

    assert result.exit_code == 0, result.output
    assert "Retire: target task fix-retry-logic" in result.output
    assert (repo / "tasks" / "retire-fix-retry-logic.md").is_file()

