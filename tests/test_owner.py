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
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


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
    return (repo / "log.md").read_text(encoding="utf-8")


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


def _owner_gate(repo: Path) -> tuple[str, Path]:
    slug, path = _make_task(repo, status="in_progress")
    ticket = Ticket.read(path)
    ticket.frontmatter["step"] = "2 (review)"
    ticket.write(path)
    return slug, path


def test_owner_gate_requires_stopped_confirmation(repo: Path) -> None:
    slug, path = _owner_gate(repo)
    before = path.read_bytes()
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 2
    assert "--assist-stopped" in result.output
    assert path.read_bytes() == before


def test_owner_gate_remains_progressable(repo: Path) -> None:
    slug, path = _owner_gate(repo)
    result = CliRunner().invoke(app, ["owner", slug, "marc", "--assist-stopped"])
    assert result.exit_code == 0, result.output
    ticket = Ticket.read(path)
    assert (ticket.owner, ticket.status, ticket.step) == ("marc", "in_progress", "2 (review)")
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    assert Ticket.read(path).status == "done"


@pytest.mark.parametrize(
    ("first_role", "gate"), [(None, True), ("owner", True), ("agent", False)]
)
def test_owner_resolves_inherited_step_role(
    repo: Path, first_role: str | None, gate: bool
) -> None:
    slug, path = _owner_gate(repo)
    ticket = Ticket.read(path)
    steps = ticket.frontmatter["workflow"]["steps"]
    steps[0].pop("assignee")
    if first_role is not None:
        steps[0]["assignee"] = first_role
    steps[1].pop("assignee")
    ticket.write(path)
    result = CliRunner().invoke(app, ["owner", slug, "marc", "--assist-stopped"])
    if gate:
        assert result.exit_code == 0, result.output
        assert (Ticket.read(path).owner, Ticket.read(path).status) == ("marc", "in_progress")
    else:
        assert result.exit_code == 2
        assert "agent step" in result.output


@pytest.mark.parametrize("other_checkout", [False, True])
def test_owner_refuses_own_supervised_session(repo: Path, monkeypatch, other_checkout) -> None:
    from coga.repl_supervisor import build_supervised_step_env
    from coga.task_env import build_task_env
    from coga.tasks import resolve_task

    slug, path = _owner_gate(repo)
    before = path.read_bytes()
    cfg = load_config(repo)
    ref = resolve_task(cfg, slug)
    source_path = repo.parent / "source-checkout" / "tasks" / path.name if other_checkout else ref.path
    env = build_task_env(cfg, ref, Ticket.read(path))
    env.update(build_supervised_step_env({}, task_path=source_path, step="2 (review)"))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("COGA_SUPERVISED", "1")
    result = CliRunner().invoke(app, ["owner", slug, "marc", "--assist-stopped"])
    assert result.exit_code == 2
    assert "supervised session" in result.output
    assert path.read_bytes() == before
