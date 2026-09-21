"""`coga.views` — the render substance extracted from the `show`/`status` heads.

These unit-test the module directly (typer-free renders + typed errors); the
end-to-end CLI paths stay covered by `tests/test_status.py`.
"""

from __future__ import annotations

import io
from pathlib import Path
from textwrap import dedent

import pytest
from rich.console import Console

from coga.config import load_config
from coga.recurring import TemplateStatus
from coga.tasks import TaskNotFoundError, TaskRef, UnknownDirectoryError
from coga.views import (
    ViewError,
    _print_recurring_templates,
    render_show,
    render_status,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


TICKET = """
---
title: X
status: draft
owner: marc
agent: claude
workflow: null
---

## Description
"""


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


def _task(company: Path, rel: str) -> Path:
    task_dir = company / "tasks" / rel
    task_dir.mkdir(parents=True)
    _write(task_dir / "ticket.md", TICKET)
    return task_dir


def _recording_console() -> Console:
    # Fixed width so ellipsizing/narrow branches are deterministic across hosts.
    return Console(file=io.StringIO(), width=120)


# --- render_show -----------------------------------------------------------


def test_render_show_prints_ticket_and_log_rules(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    console = _recording_console()

    render_show(load_config(repo), "fix-retry-logic", console=console)

    out = console.file.getvalue()
    assert "fix-retry-logic/ticket.md" in out
    assert "log (from coga/log.md)" in out


def test_render_show_unknown_task_raises(repo: Path) -> None:
    _task(repo, "fix-retry-logic")

    with pytest.raises(TaskNotFoundError):
        render_show(load_config(repo), "does-not-exist", console=_recording_console())


# --- render_status ---------------------------------------------------------


def test_render_status_lists_tasks(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    _task(repo, "ship-it")
    console = _recording_console()

    render_status(
        load_config(repo),
        directory=None,
        no_recurse=False,
        order_by="updated",
        reverse=False,
        show_all=False,
        dirs=False,
        blocked=False,
        console=console,
    )

    out = console.file.getvalue()
    assert "fix-retry-logic" in out
    assert "ship-it" in out


def test_render_status_warns_when_control_ref_ahead(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """When the fetched control ref has newer task state, the table gets a
    stderr staleness warning (stdout stays parseable)."""
    _task(repo, "fix-retry-logic")
    monkeypatch.setattr(
        "coga.views.stale_coga_task_rels",
        lambda cfg: ["coga/tasks/fix-retry-logic/ticket.md"],
    )
    console = _recording_console()

    render_status(
        load_config(repo),
        directory=None,
        no_recurse=False,
        order_by="updated",
        reverse=False,
        show_all=False,
        dirs=False,
        blocked=False,
        console=console,
    )

    err = capsys.readouterr().err
    assert "newer" in err and "1 task" in err
    assert "newer" not in console.file.getvalue()


def test_render_status_bad_order_by_raises(repo: Path) -> None:
    _task(repo, "fix-retry-logic")

    with pytest.raises(ViewError) as exc:
        render_status(
            load_config(repo),
            directory=None,
            no_recurse=False,
            order_by="bogus",
            reverse=False,
            show_all=False,
            dirs=False,
            blocked=False,
            console=_recording_console(),
        )

    assert "--order-by" in str(exc.value)


def test_render_status_unknown_directory_raises(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")

    with pytest.raises(UnknownDirectoryError):
        render_status(
            load_config(repo),
            directory="sales",
            no_recurse=False,
            order_by="updated",
            reverse=False,
            show_all=False,
            dirs=False,
            blocked=False,
            console=_recording_console(),
        )


def test_render_status_dirs_unknown_directory_raises(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")

    with pytest.raises(UnknownDirectoryError):
        render_status(
            load_config(repo),
            directory="sales",
            no_recurse=False,
            order_by="updated",
            reverse=False,
            show_all=False,
            dirs=True,
            blocked=False,
            console=_recording_console(),
        )


def test_render_status_dirs_lists_directories(repo: Path, capsys) -> None:
    # --dirs prints plain paths via print(); capsys captures stdout.
    _task(repo, "fix-retry-logic")  # a task, not a directory — must not appear
    _task(repo, "marketing/digest-sweep")
    _task(repo, "ops/rotate-keys")

    render_status(
        load_config(repo),
        directory=None,
        no_recurse=False,
        order_by="updated",
        reverse=False,
        show_all=False,
        dirs=True,
        blocked=False,
    )

    lines = capsys.readouterr().out.split()
    assert lines == ["marketing", "ops"]
    assert "fix-retry-logic" not in lines


# --- recurring footer -----------------------------------------------------------


def _template(
    name: str,
    *,
    instance: str | None = None,
    instance_status: str | None = None,
    error: str | None = None,
    stale_done: bool = False,
    serviced: bool = False,
) -> TemplateStatus:
    """A synthetic `list_templates` row; `instance` is the period task's leaf
    under `tasks/recurring/`, and the period fields the footer never reads
    are left `None`."""
    ref = (
        TaskRef(slug=instance, path=Path("coga/tasks") / "recurring" / instance, directory="recurring")
        if instance is not None
        else None
    )
    return TemplateStatus(
        name=name,
        schedule=None if error else "0 9 * * 1",
        last_fire=None,
        next_fire=None,
        period_key=None,
        target_slug=f"recurring/{name}",
        instance=ref,
        instance_status=instance_status,
        error=error,
        stale_done=stale_done,
        serviced=serviced,
    )


def _footer(templates: list[TemplateStatus]) -> list[str]:
    console = _recording_console()
    _print_recurring_templates(console, templates, leading_blank=False)
    return console.file.getvalue().splitlines()


def test_recurring_footer_is_silent_without_templates() -> None:
    assert _footer([]) == []


def test_recurring_footer_counts_period_states_via_template_due() -> None:
    """Due is `TemplateStatus.due`, not a rescan: a stale prior-period `done`
    instance counts as due (the next sweep replaces it), a serviced period
    whose task Dream reaped does not, and a live instance covers its period.
    None of them earns a named line."""
    rows = [
        _template("fresh"),
        _template("stale", instance="stale", instance_status="done", stale_done=True),
        _template("reaped", serviced=True),
        _template("live", instance="live", instance_status="in_progress"),
    ]
    assert _footer(rows) == ["Recurring: 4 templates · 2 due — coga recurring list"]


def test_recurring_footer_uses_singular_nouns() -> None:
    assert _footer([_template("only")]) == [
        "Recurring: 1 template · 1 due — coga recurring list"
    ]


def test_recurring_footer_names_errors_and_unreadable_instances() -> None:
    """Exceptions are never reduced to a count: every load error and every
    `unknown` instance gets its own line under the summary, sorted by name,
    while the healthy templates stay summarized."""
    rows = [
        _template("healthy"),
        _template("zeta", error="missing schedule"),
        _template("mystery", instance="mystery", instance_status="unknown"),
        _template("alpha", error="bad cron"),
    ]
    assert _footer(rows) == [
        "Recurring: 4 templates · 1 due · 2 errors — coga recurring list",
        "  error: alpha — bad cron",
        "  error: zeta — missing schedule",
        "  warning: mystery — instance recurring/mystery is unreadable (status unknown)",
    ]
