from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest

from coga_edge.blocker_reminders import (
    record_reminder,
    remind_blocked_tasks,
    scan_blocker_reminders,
)
from coga.config import load_config
from coga.create import create_task
from coga.logfile import append_log
from coga.recurring import SWEEP_ACTOR, SWEEP_PAUSE_SUFFIX
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import read_ticket, resolve_task


FLOW_WEBHOOK = "https://example.test/flow-webhook"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification]
        channels = ["slack"]
        [notification.slack]
        webhook = "https://example.test/flow-webhook"
        important_webhook = "https://example.test/important-webhook"
        [git]
        enabled = false
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "code.md",
        """
        ---
        name: code
        description: tiny.
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: agent
        ---

        ## implement
        Write the code.

        ## review
        Review the code.
        """,
    )
    monkeypatch.chdir(company)
    return company


def _task_with_blocker(
    repo: Path,
    *,
    status: str = "blocked",
    slug: str = "blocked",
    resolved: bool = False,
) -> str:
    ref = create_task(
        cfg=load_config(repo),
        title="Blocked work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status=status,
        slug_override=slug,
    )
    mark = "x" if resolved else " "
    body = (
        "\n## Blockers\n\n"
        f"- [{mark}] [2026-06-30 09:00] [agent:claude] "
        "id=20260630T090000 retry ceiling unspecified\n"
    )
    if resolved:
        body += "  resolved: [2026-06-30 09:30] [human:marc] cap at 5 minutes\n"
    replace_blackboard(ref["path"], body)
    return ref["slug"]


def _capture_posts(
    monkeypatch: pytest.MonkeyPatch, *, urls: list[str] | None = None
) -> list[str]:
    posts: list[str] = []

    def fake(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        if urls is not None:
            urls.append(url)
        posts.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("requests.post", fake)
    return posts


def test_scan_blocker_reminders_reads_blocked_tasks(repo: Path) -> None:
    slug = _task_with_blocker(repo)

    reminders = scan_blocker_reminders(load_config(repo))

    assert len(reminders) == 1
    reminder = reminders[0]
    assert reminder.slug == slug
    assert reminder.blocker.reason == "retry ceiling unspecified"
    assert reminder.blocker.created_at == datetime(2026, 6, 30, 9, 0)
    assert reminder.next_command == f'coga unblock {slug} --answer "..."'
    assert reminder.reminded is False


def test_scan_blocker_reminders_ignores_nonblocked_tasks(repo: Path) -> None:
    _task_with_blocker(repo, status="in_progress")

    assert scan_blocker_reminders(load_config(repo)) == []


def test_paused_recurring_blocker_is_reminded_once_without_reactivation(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = _task_with_blocker(repo, status="paused", slug="recurring/resolve-conflicts")
    cfg = load_config(repo)
    append_log(cfg, slug, SWEEP_ACTOR, f"paused — {SWEEP_PAUSE_SUFFIX}")
    posts = _capture_posts(monkeypatch)

    reminders = scan_blocker_reminders(cfg)

    assert len(reminders) == 1
    assert reminders[0].status == "paused"
    assert reminders[0].next_command == f'coga unblock {slug} --answer "..."'
    assert remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 10, 0)) == 1
    assert "is paused" in posts[0]
    assert "retry ceiling unspecified" in posts[0]
    assert f'`coga unblock {slug} --answer "..."`' in posts[0]
    assert "the next recurring sweep resumes the period" in posts[0]
    assert read_ticket(resolve_task(cfg, slug)).status == "paused"
    assert remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 11, 0)) == 0
    assert len(posts) == 1


def test_human_paused_recurring_blocker_keeps_launch_guidance(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = _task_with_blocker(repo, status="paused", slug="recurring/resolve-conflicts")
    cfg = load_config(repo)
    append_log(cfg, slug, "human:alice", "paused — holding for review")
    posts = _capture_posts(monkeypatch)

    reminders = scan_blocker_reminders(cfg)

    assert reminders[0].sweep_resumes is False
    assert reminders[0].next_command == f"coga launch {slug}"
    assert remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 10, 0)) == 1
    assert f"`coga launch {slug}`" in posts[0]
    assert f'`coga unblock {slug} --answer "..."`' in posts[0]
    assert "next recurring sweep" not in posts[0]
    assert read_ticket(resolve_task(cfg, slug)).status == "paused"


@pytest.mark.parametrize(
    ("slug", "status", "resolved"),
    [
        ("ordinary", "paused", False),
        ("recurring/parked", "paused", True),
        ("recurring/finished", "done", False),
        ("recurring/canceled", "canceled", False),
    ],
)
def test_reminders_exclude_ordinary_pauses_and_resolved_or_terminal_periods(
    repo: Path, slug: str, status: str, resolved: bool
) -> None:
    _task_with_blocker(repo, slug=slug, status=status, resolved=resolved)

    assert scan_blocker_reminders(load_config(repo)) == []


def test_paused_recurring_task_without_blockers_is_not_reminded(repo: Path) -> None:
    slug = _task_with_blocker(repo, status="paused", slug="recurring/parked")
    cfg = load_config(repo)
    replace_blackboard(resolve_task(cfg, slug).ticket_path, "\nParked by the owner.\n")

    assert scan_blocker_reminders(cfg) == []


def test_remind_blocked_tasks_posts_once_and_records_watermark(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = _task_with_blocker(repo)
    urls: list[str] = []
    posts = _capture_posts(monkeypatch, urls=urls)
    cfg = load_config(repo)

    assert remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 10, 0)) == 1
    assert urls == [FLOW_WEBHOOK]
    assert len(posts) == 1
    assert f"*{slug}*" in posts[0]
    assert "retry ceiling unspecified" in posts[0]
    assert f'`coga unblock {slug} --answer "..."`' in posts[0]

    ticket_path = repo / "tasks" / f"{slug}.md"
    blackboard = read_blackboard(ticket_path)
    assert "## Blocker reminders" in blackboard
    assert "last_reminded: 2026-06-30 10:00" in blackboard

    assert remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 11, 0)) == 0
    assert len(posts) == 1


def test_resolved_blockers_are_not_reminded(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _task_with_blocker(repo, resolved=True)
    posts = _capture_posts(monkeypatch)

    assert remind_blocked_tasks(load_config(repo)) == 0
    assert posts == []


def test_failed_watermark_write_retries_the_reminder_next_run(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The watermark follows the post, so a lost write means one more reminder."""
    from coga_edge import blocker_reminders

    slug = _task_with_blocker(repo)
    posts = _capture_posts(monkeypatch)
    cfg = load_config(repo)
    ticket_path = repo / "tasks" / f"{slug}.md"
    real_update = blocker_reminders.update_blackboard

    def refuse(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError("read-only checkout")

    monkeypatch.setattr(blocker_reminders, "update_blackboard", refuse)
    with pytest.raises(OSError, match="read-only checkout"):
        remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 10, 0))
    assert len(posts) == 1
    assert "## Blocker reminders" not in read_blackboard(ticket_path)

    monkeypatch.setattr(blocker_reminders, "update_blackboard", real_update)
    assert remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 11, 0)) == 1
    assert len(posts) == 2
    assert "last_reminded: 2026-06-30 11:00" in read_blackboard(ticket_path)
    # The fingerprint is a permanent dedup key once recorded.
    assert remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 12, 0)) == 0
    assert len(posts) == 2


@pytest.mark.parametrize("scheduled", [False, True])
def test_main_runs_from_the_edge_and_bumps_only_a_launched_script_task(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    scheduled: bool,
) -> None:
    from typer.testing import CliRunner

    from coga import runner
    from coga.cli import app
    from coga_edge import blocker_reminders

    slug = _task_with_blocker(repo)
    _capture_posts(monkeypatch)
    ref = resolve_task(load_config(repo), slug)
    bumps: list[str] = []
    monkeypatch.setattr(runner, "_bump", lambda slug: bumps.append(slug) or 0)
    # The recipe name left the registry: the unknown-recipe exit, no stub.
    removed = CliRunner().invoke(app, ["run", "blocker-reminders"])
    assert removed.exit_code == 2
    assert "unknown recipe 'blocker-reminders'" in removed.output

    monkeypatch.setenv("COGA_TASK_SLUG", slug)
    # A manual call can inherit even valid script attribution.
    monkeypatch.setenv("COGA_SCRIPT_TASK", str(ref.path))
    capsys.readouterr()
    assert blocker_reminders.main([], scheduled=scheduled) == 0
    assert "[blockers] reminded 1 blocker(s)." in capsys.readouterr().out
    assert bumps == ([slug] if scheduled else [])
    assert blocker_reminders.main(["--now"], scheduled=scheduled) == 2
    assert bumps == ([slug] if scheduled else [])
