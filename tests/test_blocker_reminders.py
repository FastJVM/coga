from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest

from coga.blocker_reminders import (
    remind_blocked_tasks,
    scan_blocker_reminders,
)
from coga.config import load_config
from coga.create import create_task
from coga.taskfile import read_blackboard, replace_blackboard


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


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
        webhook = "https://example.test/webhook"
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
          - name: review
        ---
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
        assignee="claude",
        watchers=[],
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


def _capture_posts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    posts: list[str] = []

    def fake(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        posts.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", fake)
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


def test_remind_blocked_tasks_posts_once_and_records_watermark(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = _task_with_blocker(repo)
    posts = _capture_posts(monkeypatch)
    cfg = load_config(repo)

    assert remind_blocked_tasks(cfg, now=datetime(2026, 6, 30, 10, 0)) == 1
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
