from __future__ import annotations

import time
from pathlib import Path
from textwrap import dedent

import pytest

from relay.commands.create import scaffold_task
from relay.config import load_config
from relay.lock import TaskLock
from relay.tasks import list_tasks
from relay.ticket import Ticket
from relay.validate import run


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path):
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "ready"
        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {"claude1" = "claude"}
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _write(company / "contexts" / "email" / "payment-flow" / "SKILL.md", "---\nname: x\n---\n")
    _write(company / "skills" / "infra" / "tests" / "SKILL.md", "---\nname: x\n---\n")
    return company


def test_clean_repo_has_no_issues(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=["email/payment-flow"], mode="interactive",
        owner="marc", assignee="claude1", watchers=[], status="ready",
    )
    report = run(cfg)
    assert report.issues == []
    assert report.ok_count == 1


def test_stale_lock_flagged(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    lock = TaskLock(ref.path)
    lock.acquire("claude1")
    # Rewrite the lock file with an old timestamp
    lock.path.write_text("holder: claude1\nacquired: 2020-01-01T00:00:00Z\n")
    report = run(cfg)
    kinds = [i.kind for i in report.issues]
    assert "stale-lock" in kinds


def test_broken_skill_ref(repo: Path) -> None:
    cfg = load_config(repo)
    # Directly write a ticket with a bogus skill reference in its frozen workflow.
    task_dir = repo / "tasks" / "001-x"
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent("""
        ---
        title: X
        status: active
        mode: interactive
        assignee: claude1
        owner: marc
        workflow:
          name: x
          steps:
            - name: a
              skill: does/not/exist
        step: 1 (a)
        ---

        ## Description
    """).lstrip())
    (task_dir / "blackboard.md").write_text("# Blackboard\n")
    (task_dir / "log.md").write_text("")
    report = run(cfg)
    assert any(i.kind == "broken-skill" for i in report.issues)


def test_invalid_status(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="ready",
    )
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["status"] = "bogus"
    t.write(ref.path / "ticket.md")
    report = run(cfg)
    assert any(i.kind == "invalid-status" for i in report.issues)


def test_missing_file(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="ready",
    )
    ref = list_tasks(cfg)[0]
    (ref.path / "blackboard.md").unlink()
    report = run(cfg)
    assert any(i.kind == "missing-file" and "blackboard" in i.message for i in report.issues)


def test_stuck_active_flagged(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    # Backdate log.md's mtime
    old = time.time() - 100 * 3600  # 100 hours ago
    import os
    os.utime(ref.path / "log.md", (old, old))
    report = run(cfg, idle_hours=72.0)
    assert any(i.kind == "stuck-active" for i in report.issues)
