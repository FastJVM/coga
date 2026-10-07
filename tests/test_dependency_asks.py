"""Tests for `coga.dependency_asks` and its two consumers.

`coga validate` warns `dead-dependency`; `coga mark canceled` lists the
dependents its cancel stranded. Neither rewrites the dependent's ask.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.blackboard import append_blocker, open_blockers
from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.dependency_asks import (
    CANCELED,
    MISSING,
    RETIRED,
    dead_dependency_asks,
    named_dependencies,
    successor_from_reason,
)
from coga.logfile import append_log
from coga.tasks import list_tasks
from coga.validate import run as validate_run


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
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "one.md",
        """
        ---
        name: one
        description: tiny.
        steps:
          - name: work
            assignee: agent
        ---

        ## work
        Do it.
        """,
    )
    monkeypatch.chdir(company)
    return company


def _task(repo: Path, title: str, status: str = "draft") -> tuple[str, Path]:
    ref = create_task(
        cfg=load_config(repo),
        title=title,
        workflow_name="one",
        contexts=[],
        owner="marc",
        agent="claude",
        status=status,
    )
    return ref["slug"], ref["path"]


def _blocked_on(repo: Path, target: str) -> tuple[str, Path]:
    slug, path = _task(repo, "Dependent work", status="blocked")
    append_blocker(path, "human:marc", f"Depends on {target}: needs its schema")
    return slug, path


def _dead(repo: Path):
    cfg = load_config(repo)
    return dead_dependency_asks(cfg, list_tasks(cfg))


def test_named_dependencies_reads_the_lifecycle_convention() -> None:
    assert named_dependencies("Depends on v2/schema: needs it") == ["v2/schema"]
    assert named_dependencies("Depends on `a-b`. Also Depends on c.") == [
        "a-b",
        "c",
    ]
    assert named_dependencies("Waiting on legal review") == []


def test_successor_from_reason() -> None:
    assert successor_from_reason("Superseded by v2/new (2026-10-01)") == "v2/new"
    assert successor_from_reason("Obsolete") is None
    assert successor_from_reason(None) is None


def test_live_dependency_is_not_reported(repo: Path) -> None:
    target, _ = _task(repo, "Schema", status="active")
    _blocked_on(repo, target)

    assert _dead(repo) == []


def test_canceled_dependency_reports_successor(repo: Path) -> None:
    target, _ = _task(repo, "Schema", status="active")
    successor, _ = _task(repo, "Schema v2", status="active")
    dependent, _ = _blocked_on(repo, target)

    result = CliRunner().invoke(
        app,
        ["mark", "canceled", target, "--message", f"Superseded by {successor}"],
    )

    assert result.exit_code == 0, result.output
    assert f"named {target} and will not drain" in result.output
    assert dependent in result.output
    [dead] = _dead(repo)
    assert (dead.dependent, dead.target, dead.state) == (
        dependent,
        target,
        CANCELED,
    )
    assert dead.successor == successor
    assert f"Depends on {successor}" in dead.remedy()


def test_cancel_with_no_dependents_prints_nothing_extra(repo: Path) -> None:
    target, _ = _task(repo, "Schema", status="active")

    result = CliRunner().invoke(
        app, ["mark", "canceled", target, "--message", "Obsolete"]
    )

    assert result.exit_code == 0, result.output
    assert "will not drain" not in result.output


def test_renamed_dependency_is_missing(repo: Path) -> None:
    target, target_path = _task(repo, "Schema", status="active")
    dependent, dependent_path = _blocked_on(repo, target)
    shutil.move(target_path, target_path.with_name("schema-renamed.md"))

    [dead] = _dead(repo)

    assert (dead.dependent, dead.state) == (dependent, MISSING)
    # Reporting never touches the dependent's ask.
    assert len(open_blockers(dependent_path)) == 1


def test_retired_dependency_is_satisfied(repo: Path) -> None:
    target, target_path = _task(repo, "Schema", status="active")
    _blocked_on(repo, target)
    append_log(load_config(repo), target, "agent:claude", "task done")
    target_path.unlink()

    [dead] = _dead(repo)

    assert dead.state == RETIRED
    assert "coga unblock" in dead.remedy()


def test_validate_warns_dead_dependency(repo: Path) -> None:
    target, _ = _task(repo, "Schema", status="active")
    dependent, _ = _blocked_on(repo, target)
    CliRunner().invoke(app, ["mark", "canceled", target, "--message", "Obsolete"])

    issues = [
        issue
        for issue in validate_run(load_config(repo)).issues
        if issue.kind == "dead-dependency"
    ]

    assert [(issue.task, issue.severity) for issue in issues] == [
        (dependent, "warn")
    ]
    assert f"{target} was canceled" in issues[0].message
