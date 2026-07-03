"""`coga status` directory filtering.

Tasks are directories with `ticket.md` anywhere under `tasks/`, and the filter
narrows the listing to a directory sub-tree
(nested tasks included), to a single directory level (`--no-recurse`), and
fails loud on an unknown directory.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.tasks import (
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


def test_filter_no_recurse_top_level_keeps_only_top_level(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    _task(repo, "ship-it")
    _task(repo, "marketing/digest-sweep")
    cfg = load_config(repo)

    refs = filter_tasks_under(list_tasks(cfg), None, cfg, recurse=False)

    assert [r.id_slug for r in refs] == ["fix-retry-logic", "ship-it"]


def test_filter_no_recurse_directory_keeps_only_direct_children(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")
    cfg = load_config(repo)

    refs = filter_tasks_under(list_tasks(cfg), "marketing", cfg, recurse=False)

    # The nested task under marketing/social is excluded.
    assert [r.id_slug for r in refs] == ["marketing/digest-sweep"]


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


def test_status_no_recurse_lists_only_top_level(repo: Path) -> None:
    _task(repo, "fix-retry-logic")
    _task(repo, "marketing/digest-sweep")

    result = CliRunner().invoke(app, ["status", "--no-recurse"])

    assert result.exit_code == 0
    assert "fix-retry-logic" in result.stdout
    assert "digest-sweep" not in result.stdout


def test_status_directory_no_recurse_excludes_nested(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")

    result = CliRunner().invoke(app, ["status", "marketing", "--no-recurse"])

    assert result.exit_code == 0
    assert "digest-sweep" in result.stdout
    assert "marketing/social/relaunch" not in result.stdout


def test_status_unknown_directory_fails_loud(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")

    result = CliRunner().invoke(app, ["status", "sales"])

    assert result.exit_code == 2
    assert "Unknown directory 'sales'" in result.output
    assert "marketing" in result.output


# --- status --dirs ---------------------------------------------------------


def test_status_dirs_lists_all_directories_not_tasks(repo: Path) -> None:
    _task(repo, "fix-retry-logic")  # a task, not a directory — must not appear
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")
    _task(repo, "ops/rotate-keys")

    result = CliRunner().invoke(app, ["status", "--dirs"])

    assert result.exit_code == 0
    lines = result.stdout.split()
    assert lines == ["marketing", "marketing/social", "ops"]
    assert "fix-retry-logic" not in result.stdout


def test_status_dirs_no_recurse_keeps_only_top_level(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")
    _task(repo, "ops/rotate-keys")

    result = CliRunner().invoke(app, ["status", "--dirs", "--no-recurse"])

    assert result.exit_code == 0
    lines = result.stdout.split()
    assert lines == ["marketing", "ops"]


def test_status_dirs_under_directory_excludes_the_query_itself(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")
    _task(repo, "marketing/social/relaunch")
    _task(repo, "marketing/social/paid/promo")

    result = CliRunner().invoke(app, ["status", "marketing", "--dirs"])

    assert result.exit_code == 0
    lines = result.stdout.split()
    assert lines == ["marketing/social", "marketing/social/paid"]
    assert "marketing\n" not in result.stdout


def test_status_dirs_under_directory_no_recurse_is_immediate_level(repo: Path) -> None:
    _task(repo, "marketing/social/relaunch")
    _task(repo, "marketing/social/paid/promo")

    result = CliRunner().invoke(app, ["status", "marketing", "--dirs", "--no-recurse"])

    assert result.exit_code == 0
    lines = result.stdout.split()
    assert lines == ["marketing/social"]


def test_status_dirs_unknown_directory_fails_loud(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")

    result = CliRunner().invoke(app, ["status", "sales", "--dirs"])

    assert result.exit_code == 2
    assert "Unknown directory 'sales'" in result.output


def test_status_dirs_empty_prints_note(repo: Path) -> None:
    _task(repo, "fix-retry-logic")  # only top-level tasks, no plain directories

    result = CliRunner().invoke(app, ["status", "--dirs"])

    assert result.exit_code == 0
    assert "no directories" in result.stdout


# --- --order-by created ----------------------------------------------------


def test_status_order_by_created_lists_oldest_first(repo: Path) -> None:
    """`created` shows the exact order the megalaunch drain services tickets."""
    from coga.paths import log_path

    _task(repo, "alpha")
    _task(repo, "beta")
    # beta's create line is older, so it sorts first despite slug order.
    log_path(load_config(repo)).write_text(
        "2026-06-02 10:00 [alpha] [human:marc] created\n"
        "2026-06-01 10:00 [beta] [human:marc] created\n"
    )

    result = CliRunner().invoke(app, ["status", "--order-by", "created"])

    assert result.exit_code == 0, result.output
    assert result.output.index("beta") < result.output.index("alpha")


def test_status_order_by_created_reverse_lists_newest_first(repo: Path) -> None:
    from coga.paths import log_path

    _task(repo, "alpha")
    _task(repo, "beta")
    log_path(load_config(repo)).write_text(
        "2026-06-02 10:00 [alpha] [human:marc] created\n"
        "2026-06-01 10:00 [beta] [human:marc] created\n"
    )

    result = CliRunner().invoke(app, ["status", "--order-by", "created", "--reverse"])

    assert result.exit_code == 0, result.output
    assert result.output.index("alpha") < result.output.index("beta")
