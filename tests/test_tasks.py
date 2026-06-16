"""Task discovery and resolution, including tasks nested in sub-directories."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay.config import load_config
from relay.tasks import (
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
    nested = _task(repo, "marketing/digest-sweep")

    refs = list_tasks(load_config(repo))

    # Sorted by id_slug: "fix-retry-logic" < "marketing/digest-sweep".
    assert [(r.id_slug, r.path) for r in refs] == [
        ("fix-retry-logic", top),
        ("marketing/digest-sweep", nested),
    ]


def test_nested_task_gets_path_qualified_id_slug(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")

    ref = list_tasks(load_config(repo))[0]

    assert ref.slug == "digest-sweep"
    assert ref.directory == "marketing"
    assert ref.id_slug == "marketing/digest-sweep"


def test_list_tasks_finds_tasks_at_any_depth(repo: Path) -> None:
    top = _task(repo, "fix-retry-logic")
    one = _task(repo, "marketing/digest-sweep")
    deep = _task(repo, "marketing/social/relaunch")

    refs = list_tasks(load_config(repo))

    assert [(r.id_slug, r.directory, r.path) for r in refs] == [
        ("fix-retry-logic", None, top),
        ("marketing/digest-sweep", "marketing", one),
        ("marketing/social/relaunch", "marketing/social", deep),
    ]


def test_list_tasks_does_not_recurse_into_a_task_dir(repo: Path) -> None:
    # A `ticket.md` makes a directory a task; nothing inside it is discovered,
    # even if it happens to contain another `ticket.md`.
    outer = _task(repo, "outer")
    _write(outer / "inner" / "ticket.md", TICKET)

    refs = list_tasks(load_config(repo))

    assert [r.id_slug for r in refs] == ["outer"]


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


def test_same_leaf_name_in_different_groups_coexists(repo: Path) -> None:
    marketing = _task(repo, "marketing/digest")
    eng = _task(repo, "eng/digest")

    refs = list_tasks(load_config(repo))

    assert [(r.id_slug, r.path) for r in refs] == [
        ("eng/digest", eng),
        ("marketing/digest", marketing),
    ]


def test_top_level_and_grouped_leaf_can_share_a_name(repo: Path) -> None:
    top = _task(repo, "digest")
    nested = _task(repo, "marketing/digest")

    refs = {r.id_slug: r.path for r in list_tasks(load_config(repo))}

    assert refs == {"digest": top, "marketing/digest": nested}


def test_resolve_task_finds_nested_task_by_qualified_slug_and_prefix(repo: Path) -> None:
    nested = _task(repo, "marketing/digest-sweep")
    _task(repo, "fix-retry-logic")
    cfg = load_config(repo)

    assert resolve_task(cfg, "marketing/digest-sweep").path == nested
    assert resolve_task(cfg, "marketing/dig").path == nested


def test_resolve_task_rejects_bare_leaf_of_nested_task(repo: Path) -> None:
    _task(repo, "marketing/digest-sweep")
    cfg = load_config(repo)

    with pytest.raises(TaskNotFoundError, match="No task matches"):
        resolve_task(cfg, "digest-sweep")


def test_resolve_task_prefix_ambiguity_spans_top_level_and_directory(repo: Path) -> None:
    # Both id_slugs start with "auto": a top-level task and a task directory.
    _task(repo, "auto-pilot")
    _task(repo, "auto/sweep")
    cfg = load_config(repo)

    with pytest.raises(TaskNotFoundError, match="Ambiguous"):
        resolve_task(cfg, "auto")
