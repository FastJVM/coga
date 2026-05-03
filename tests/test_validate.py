from __future__ import annotations

import time
from pathlib import Path
from textwrap import dedent

import pytest

import requests

from relay.scaffold import scaffold_task
from relay.config import load_config
from relay.lock import TaskLock
from relay.tasks import list_tasks
from relay.ticket import Ticket
from relay.validate import apply_safe_fixes, probe_slack, run


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
        default_status = "draft"
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
        owner="marc", assignee="claude1", watchers=[], status="draft",
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


def test_unfrozen_workflow_string_does_not_crash(repo: Path) -> None:
    """Hand-authored tickets carrying `workflow: <name>` (a string ref) used
    to crash the validator at `wf.get("steps", [])`. Regression: surface
    them as a warning instead."""
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    t.frontmatter["workflow"] = "code/with-review"
    t.write(ref.path / "ticket.md")
    report = run(cfg)
    kinds = [i.kind for i in report.issues]
    assert "unfrozen-workflow" in kinds


def test_invalid_status(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="draft",
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
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    (ref.path / "blackboard.md").unlink()
    report = run(cfg)
    assert any(i.kind == "missing-file" and "blackboard" in i.message for i in report.issues)


def test_apply_safe_fixes_creates_missing_workspace_files(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    (ref.path / "blackboard.md").unlink()
    (ref.path / "log.md").unlink()

    fixes = apply_safe_fixes(cfg)

    assert [fix.message for fix in fixes] == [
        "created blackboard.md",
        "created log.md",
    ]
    assert (ref.path / "blackboard.md").is_file()
    assert (ref.path / "log.md").is_file()
    assert (ref.path / "log.md").read_text() == ""


def test_run_fix_repairs_before_reporting(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    (ref.path / "blackboard.md").unlink()

    report = run(cfg, fix=True)

    assert len(report.fixes) == 1
    assert report.fixes[0].message == "created blackboard.md"
    assert not any(i.kind == "missing-file" for i in report.issues)


def test_large_blackboard_warns(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude1",
        watchers=[], status="draft",
    )
    ref = list_tasks(cfg)[0]
    (ref.path / "blackboard.md").write_text("x" * 2048)

    report = run(cfg, max_blackboard_bytes=1024)
    issue = next(i for i in report.issues if i.kind == "large-blackboard")
    assert issue.severity == "warn"
    assert "included in launch prompts" in issue.message


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def _fake_post_factory(response: _FakeResponse | Exception):
    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(response, Exception):
            raise response
        return response

    return fake_post


def test_probe_slack_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.validate.requests.post",
        _fake_post_factory(_FakeResponse(400, "no_text")),
    )
    status, detail = probe_slack("https://hooks.slack.com/services/x")
    assert status == "live"
    assert "400" in detail


def test_probe_slack_revoked_by_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.validate.requests.post",
        _fake_post_factory(_FakeResponse(404, "no_service")),
    )
    status, _ = probe_slack("https://hooks.slack.com/services/x")
    assert status == "revoked"


def test_probe_slack_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "relay.validate.requests.post",
        _fake_post_factory(requests.ConnectionError("dns fail")),
    )
    status, detail = probe_slack("https://hooks.slack.com/services/x")
    assert status == "unreachable"
    assert "ConnectionError" in detail


def test_run_check_slack_emits_issue_for_revoked(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Add slack webhook to the repo's config.
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[slack]\nwebhook = "https://hooks.slack.com/services/dead"\n'
    )
    monkeypatch.setattr(
        "relay.validate.requests.post",
        _fake_post_factory(_FakeResponse(404, "no_service")),
    )
    cfg = load_config(repo)
    report = run(cfg, check_slack=True)
    kinds = [i.kind for i in report.issues]
    assert "slack-revoked" in kinds


def test_run_no_slack_check_by_default(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[slack]\nwebhook = "https://hooks.slack.com/services/dead"\n'
    )

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("network must not be called when --check-slack is off")

    monkeypatch.setattr("relay.validate.requests.post", boom)
    cfg = load_config(repo)
    run(cfg)  # must not raise


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
