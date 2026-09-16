"""Tests for `coga owner <slug> <name>`."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.ticket import Ticket


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
        company / "workflows" / "code.md",
        """
        ---
        name: code
        description: tiny.
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: owner
        ---

        ## implement
        Write the code.

        ## review
        Review it.
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(
    repo: Path, *, workflow: str | None = "code", status: str = "draft"
) -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Work",
        workflow_name=workflow,
        contexts=[],
        owner="zach",
        agent="claude",
        status=status,
    )
    return ref["slug"], ref["path"]


def _read_log(repo: Path) -> str:
    return (repo / "log.md").read_text()


@pytest.mark.parametrize("status", ["draft", "active", "paused", "blocked"])
def test_owner_reassigns_non_terminal_ticket(repo: Path, status: str) -> None:
    slug, task_path = _make_task(repo, status=status)
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.owner == "marc"
    assert t.status == status
    assert f"[{slug}] [human:marc] owner 'zach' → 'marc'" in _read_log(repo)


def test_owner_preserves_step_and_body(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="paused")
    before = Ticket.read(task_path)
    before.frontmatter["step"] = "2 (review)"
    before.write(task_path)
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 0, result.output
    after = Ticket.read(task_path)
    assert after.step == "2 (review)"
    assert after.body == before.body


def test_owner_accepts_workflow_less_draft(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None)
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 0, result.output
    assert Ticket.read(task_path).owner == "marc"


def test_owner_refuses_in_progress(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="in_progress")
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 2
    assert "in_progress" in result.output
    assert f"coga mark paused {slug}" in result.output
    assert Ticket.read(task_path).owner == "zach"
    assert "owner" not in _read_log(repo)


@pytest.mark.parametrize("status", ["done", "canceled"])
def test_owner_refuses_terminal_status(repo: Path, status: str) -> None:
    slug, task_path = _make_task(repo, status=status)
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 2
    assert status in result.output
    assert Ticket.read(task_path).owner == "zach"


def test_owner_same_owner_errors(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    result = CliRunner().invoke(app, ["owner", slug, "zach"])
    assert result.exit_code == 2
    assert "already owned by 'zach'" in result.output
    assert "owner" not in _read_log(repo)


def test_owner_requires_non_empty_name(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    result = CliRunner().invoke(app, ["owner", slug, "   "])
    assert result.exit_code == 2
    assert "cannot be empty" in result.output
    assert Ticket.read(task_path).owner == "zach"


def test_owner_unknown_task_errors(repo: Path) -> None:
    result = CliRunner().invoke(app, ["owner", "no-such-task", "marc"])
    assert result.exit_code == 2
    assert "no-such-task" in result.output


def test_owner_lands_reassignment_and_audit_line_on_control(git_repo) -> None:
    """The reassignment reaches control like any other lifecycle write."""
    cfg = load_config(git_repo.coga_os)
    ref = create_task(
        cfg=cfg,
        title="Hand this over",
        workflow_name="code",
        contexts=[],
        owner="zach",
        agent="claude",
        status="paused",
    )

    result = CliRunner().invoke(app, ["owner", ref["slug"], "marc"])

    assert result.exit_code == 0, result.output
    task_rel = str(Path(ref["path"]).relative_to(git_repo.root))
    control_ticket = Ticket.parse(
        git_repo.git("show", f"main:{task_rel}", cwd=git_repo.origin)
    )
    control_log = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert control_ticket.owner == "marc"
    assert control_ticket.status == "paused"
    assert f"[{ref['slug']}] [human:marc] owner 'zach' → 'marc'" in control_log
    assert git_repo.origin_subjects()[0] == f"Ticket: {ref['slug']} — owner marc"
    assert git_repo.git("status", "--short") == ""
