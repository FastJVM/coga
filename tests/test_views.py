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
from coga.tasks import TaskNotFoundError, UnknownDirectoryError
from coga.views import (
    VIEW_TARGET_ENV,
    ViewError,
    render_show,
    render_show_from_env,
    render_status,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


TICKET = """
---
title: X
status: draft
mode: agent
owner: marc
human: marc
agent: claude
assignee: claude
contexts: []
skills: []
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


# --- render_show_from_env --------------------------------------------------


def test_render_show_from_env_reads_target(repo: Path, capsys) -> None:
    _task(repo, "fix-retry-logic")

    # The target comes from the env contract, mirroring finalize_authored_from_env;
    # render_show_from_env constructs its own console, so capture via capsys.
    render_show_from_env(
        load_config(repo),
        environ={VIEW_TARGET_ENV: "fix-retry-logic"},
    )

    assert "fix-retry-logic/ticket.md" in capsys.readouterr().out


def test_render_show_from_env_missing_target_raises(repo: Path) -> None:
    with pytest.raises(ViewError) as exc:
        render_show_from_env(load_config(repo), environ={})

    assert VIEW_TARGET_ENV in str(exc.value)


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
