"""Task discovery and resolution, including one-level group directories."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay.config import load_config
from relay.tasks import (
    DuplicateTaskSlugError,
    TaskNotFoundError,
    list_tasks,
    resolve_task,
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
    return company


def _task(company: Path, rel: str) -> Path:
    task_dir = company / "tasks" / rel
    task_dir.mkdir(parents=True)
    _write(task_dir / "ticket.md", TICKET)
    return task_dir


def test_list_tasks_finds_tasks_one_level_inside_group_dirs(repo: Path) -> None:
    top = _task(repo, "fix-retry-logic")
    nested = _task(repo, "auto/digest-sweep")

    refs = list_tasks(load_config(repo))

    assert [(r.slug, r.path) for r in refs] == [
        ("digest-sweep", nested),
        ("fix-retry-logic", top),
    ]


def test_nested_task_keeps_bare_leaf_slug(repo: Path) -> None:
    _task(repo, "auto/digest-sweep")

    ref = list_tasks(load_config(repo))[0]

    assert ref.slug == "digest-sweep"
    assert ref.id_slug == "digest-sweep"


def test_underscore_dirs_skipped_at_both_levels(repo: Path) -> None:
    _task(repo, "_template")
    _task(repo, "auto/_draft")
    _task(repo, "_group/hidden")
    _task(repo, "auto/visible")

    refs = list_tasks(load_config(repo))

    assert [r.slug for r in refs] == ["visible"]


def test_task_dirs_are_not_recursed_into(repo: Path) -> None:
    parent = _task(repo, "parent-task")
    inner = parent / "inner-task"
    inner.mkdir()
    _write(inner / "ticket.md", TICKET)

    refs = list_tasks(load_config(repo))

    assert [r.slug for r in refs] == ["parent-task"]


def test_group_dir_without_tickets_is_ignored(repo: Path) -> None:
    (repo / "tasks" / "notes").mkdir(parents=True)
    _write(repo / "tasks" / "notes" / "scratch.md", "not a ticket\n")
    _task(repo, "real-task")

    refs = list_tasks(load_config(repo))

    assert [r.slug for r in refs] == ["real-task"]


def test_duplicate_leaf_slug_raises_typed_error(repo: Path) -> None:
    top = _task(repo, "dup-task")
    nested = _task(repo, "auto/dup-task")

    with pytest.raises(DuplicateTaskSlugError) as exc_info:
        list_tasks(load_config(repo))

    assert exc_info.value.slug == "dup-task"
    assert set(exc_info.value.paths) == {top, nested}


def test_resolve_task_finds_nested_task_by_slug_and_prefix(repo: Path) -> None:
    nested = _task(repo, "auto/digest-sweep")
    _task(repo, "fix-retry-logic")
    cfg = load_config(repo)

    assert resolve_task(cfg, "digest-sweep").path == nested
    assert resolve_task(cfg, "dig").path == nested


def test_resolve_task_prefix_ambiguity_spans_groups(repo: Path) -> None:
    _task(repo, "auto/fix-digest")
    _task(repo, "fix-retry-logic")
    cfg = load_config(repo)

    with pytest.raises(TaskNotFoundError, match="Ambiguous"):
        resolve_task(cfg, "fix")
