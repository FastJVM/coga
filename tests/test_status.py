"""`relay status` directory filtering.

Tasks are directories with `ticket.md` anywhere under `tasks/`, and the filter
narrows the listing to a directory sub-tree
(nested tasks included), to the top level (`root`), and fails loud on an
unknown directory.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.tasks import (
    UnknownDirectoryError,
    filter_tasks_under,
    list_task_dirs,
    list_tasks,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


TICKET = """
---
title: X
status: draft
mode: interactive
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
    monkeypatch.chdir(company)
    return company


def _task(company: Path, rel: str) -> Path:
    task_dir = company / "tasks" / rel
    task_dir.mkdir(parents=True)
    _write(task_dir / "ticket.md", TICKET)
    return task_dir


# --- list_task_dirs --------------------------------------------------------


def test_list_task_dirs_returns_non_task_dirs_at_any_depth(repo: Path) -> None:
    _task(repo, "fix-retry-logic")  # top-level task, not a directory to filter
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")
    _task(repo, "ops/rotate-keys")

    assert list_task_dirs(load_config(repo)) == [
        "marketing",
        "marketing/social",
        "ops",
    ]


def test_list_task_dirs_includes_empty_dir(repo: Path) -> None:
    # A directory exists because `mkdir` made it, even before it holds a task.
    (repo / "tasks" / "marketing").mkdir(parents=True)

    assert list_task_dirs(load_config(repo)) == ["marketing"]


# --- filter_tasks_under ----------------------------------------------------


def test_filter_keeps_whole_subtree(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")
    _task(repo, "ops/rotate-keys")
    cfg = load_config(repo)

    refs = filter_tasks_under(list_tasks(cfg), "marketing", cfg)

    # The nested task under marketing/social is included.
    assert [r.id_slug for r in refs] == [
        "marketing/digest-sweep",
        "marketing/social/relaunch",
    ]


def test_filter_by_nested_directory(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")
    cfg = load_config(repo)

    refs = filter_tasks_under(list_tasks(cfg), "marketing/social", cfg)

    assert [r.id_slug for r in refs] == ["marketing/social/relaunch"]


def test_filter_by_root_keeps_only_top_level(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    _task(repo, "ship-it")
    _task(repo, "marketing/digest-sweep")
    cfg = load_config(repo)

    refs = filter_tasks_under(list_tasks(cfg), "root", cfg)

    assert [r.id_slug for r in refs] == ["fix-retry-logic", "ship-it"]


def test_filter_by_empty_known_dir_is_not_an_error(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")
    (repo / "tasks" / "ops").mkdir(parents=True)  # known but empty directory
    cfg = load_config(repo)

    assert filter_tasks_under(list_tasks(cfg), "ops", cfg) == []


def test_filter_unknown_directory_raises_with_available(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")
    _task(repo, "ops/rotate-keys")
    cfg = load_config(repo)

    with pytest.raises(UnknownDirectoryError) as exc:
        filter_tasks_under(list_tasks(cfg), "sales", cfg)

    assert exc.value.available == ["marketing", "ops"]
    assert "marketing" in str(exc.value)
    assert "ops" in str(exc.value)


def test_filter_none_returns_everything_unchanged(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    _task(repo, "marketing/digest-sweep")
    cfg = load_config(repo)

    refs = list_tasks(cfg)
    assert filter_tasks_under(refs, None, cfg) == refs


# --- end-to-end via the CLI ------------------------------------------------


def test_status_directory_filter_lists_subtree(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")

    result = CliRunner().invoke(app, ["status", "marketing"])

    assert result.exit_code == 0
    assert "digest-sweep" in result.stdout
    assert "marketing/social/relaunch" in result.stdout
    assert "fix-retry-logic" not in result.stdout


def test_status_root_filter_lists_only_top_level(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    _task(repo, "marketing/digest-sweep")

    result = CliRunner().invoke(app, ["status", "root"])

    assert result.exit_code == 0
    assert "fix-retry-logic" in result.stdout
    assert "digest-sweep" not in result.stdout


def test_status_unknown_directory_fails_loud(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")

    result = CliRunner().invoke(app, ["status", "sales"])

    assert result.exit_code == 2
    assert "Unknown directory 'sales'" in result.output
    assert "marketing" in result.output
