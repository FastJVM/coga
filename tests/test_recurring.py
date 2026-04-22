from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest

from relay.config import load_config
from relay.recurring import check_recurring
from relay.tasks import list_tasks
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path):
    company = tmp_path / "relay-os"
    project = tmp_path / "projects" / "email-tool"
    project.mkdir(parents=True)
    _write(
        company / "relay.toml",
        f"""
        version = 1
        [projects.email-tool]
        type = "local"
        default_status = "ready"
        [agents.claude]
        cli = "claude"
        interactive = "-i"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {{"claude1" = "claude"}}
        """,
    )
    _write(company / "relay.local.toml", f'user = "marc"\n[paths]\nemail-tool = "{project}"\n')
    _write(
        company / "recurring" / "weekly-check.md",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        mode: auto
        assignee: claude1
        owner: marc
        project: email-tool
        ---

        ## Description

        Run the full deliverability diagnostic suite.
        """,
    )
    return company


def test_check_recurring_creates_task(repo: Path) -> None:
    cfg = load_config(repo)
    fixed_now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am
    created = check_recurring(cfg, now=fixed_now)
    assert len(created) == 1
    ref = created[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    assert ticket.title == "Weekly deliverability check"
    assert ticket.mode == "auto"
    assert ticket.owner == "marc"
    # Period key for weekly = ISO week of the firing (Mon 2026-04-20, ISO week 17)
    assert ref.slug.endswith("-2026-W17")
    # Description body made it in
    body = (ref.path / "ticket.md").read_text()
    assert "Run the full deliverability diagnostic suite" in body


def test_check_recurring_idempotent(repo: Path) -> None:
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = check_recurring(cfg, now=now)
    second = check_recurring(cfg, now=now)
    assert len(first) == 1
    assert len(second) == 0
    assert len(list_tasks(cfg, "email-tool")) == 1


def test_check_recurring_different_period_creates_new(repo: Path) -> None:
    cfg = load_config(repo)
    check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    created = check_recurring(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18
    assert len(created) == 1
    assert created[0].slug.endswith("-2026-W18")


def test_check_recurring_skips_bad_template(repo: Path, capsys) -> None:
    _write(repo / "recurring" / "bad.md", "no frontmatter here\n")
    cfg = load_config(repo)
    created = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(created) == 1  # good one still created
    assert "skipping bad.md" in capsys.readouterr().err
