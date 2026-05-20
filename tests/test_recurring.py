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
    _write(
        company / "recurring" / "weekly-check.md",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the full deliverability diagnostic suite.
        """,
    )
    return company


def test_check_recurring_creates_task(repo: Path) -> None:
    cfg = load_config(repo)
    fixed_now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am
    result = check_recurring(cfg, now=fixed_now)
    assert len(result.created) == 1
    assert result.errors == []
    ref = result.created[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    assert ticket.title == "Weekly deliverability check"
    assert ticket.mode == "interactive"
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
    assert len(first.created) == 1
    assert len(second.created) == 0
    assert len(list_tasks(cfg)) == 1


def test_check_recurring_different_period_creates_new(repo: Path) -> None:
    cfg = load_config(repo)
    check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    result = check_recurring(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18
    assert len(result.created) == 1
    assert result.created[0].slug.endswith("-2026-W18")


def test_check_recurring_skips_bad_template(repo: Path, capsys) -> None:
    _write(repo / "recurring" / "bad.md", "no frontmatter here\n")
    cfg = load_config(repo)
    result = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(result.created) == 1  # good one still created
    assert len(result.errors) == 1
    assert result.errors[0][0] == "bad.md"
    assert "skipping bad.md" in capsys.readouterr().err


def test_check_recurring_skips_auto_mode_template(repo: Path, capsys) -> None:
    """`mode: auto` templates are skipped with a stderr + result-errors note.

    Auto launches produce no live console output, so scheduled runs would
    sit silently. Until streaming lands, the recurring scanner refuses
    to scaffold them.
    """
    _write(
        repo / "recurring" / "daily-auto.md",
        """
        ---
        schedule: "0 9 * * *"
        title: "Daily auto"
        mode: auto
        assignee: claude
        owner: marc
        ---

        ## Description

        Auto.
        """,
    )
    cfg = load_config(repo)
    result = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    # Good (interactive) template still creates; auto one is skipped + reported.
    assert len(result.created) == 1
    assert result.created[0].slug.startswith("weekly-check-")
    assert len(result.errors) == 1
    name, msg = result.errors[0]
    assert name == "daily-auto.md"
    assert "mode=auto is temporarily disabled" in msg
    assert "skipping daily-auto.md" in capsys.readouterr().err


def test_check_recurring_skips_template_without_explicit_mode(
    repo: Path, capsys
) -> None:
    """Templates without `mode:` are treated as auto (legacy default) and skipped."""
    _write(
        repo / "recurring" / "no-mode.md",
        """
        ---
        schedule: "0 9 * * *"
        title: "No mode"
        assignee: claude
        owner: marc
        ---

        ## Description

        Legacy template.
        """,
    )
    cfg = load_config(repo)
    result = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert any(name == "no-mode.md" for name, _ in result.errors)


def test_check_recurring_skips_underscore_template(repo: Path, capsys) -> None:
    # `_template.md` is a scaffold, not a live recurring task — must be ignored
    # silently (no stderr complaint) even though its placeholder fields wouldn't
    # validate.
    _write(
        repo / "recurring" / "_template.md",
        """
        ---
        schedule: "0 9 * * 1"
        title: placeholder
        ---
        """,
    )
    cfg = load_config(repo)
    result = check_recurring(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(result.created) == 1  # only the real one
    assert result.errors == []
    assert "_template.md" not in capsys.readouterr().err
