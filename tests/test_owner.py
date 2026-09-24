"""Tests for `coga owner <slug> <name>`."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga import git
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

    git.sync_task_state(cfg, Path(ref["path"]), message="Seed ticket", strict=True)
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


@pytest.mark.parametrize("generation", ["pending:claim", "claim", "released:claim"])
def test_owner_never_invalidates_launch_claim(repo: Path, generation: str) -> None:
    slug, path = _owner_gate(repo)
    ticket = Ticket.read(path)
    ticket.frontmatter["launch_generation"] = generation
    ticket.write(path)
    before = path.read_bytes()
    result = CliRunner().invoke(app, ["owner", slug, "marc", "--assist-stopped"])
    assert result.exit_code == 2
    assert "launch claim" in result.output
    assert path.read_bytes() == before


def test_owner_preserves_edit_during_validation(repo: Path, monkeypatch) -> None:
    from coga.commands import owner as command

    slug, path = _make_task(repo, status="paused")
    original_validate = command.assert_task_valid
    newer = Ticket.read(path)
    newer.frontmatter.update(status="in_progress", launch_generation="new-launch")
    newer.body += "\nNew concurrent notes.\n"

    def concurrent_validation(*args, **kwargs):
        original_validate(*args, **kwargs)
        newer.write(path)

    monkeypatch.setattr(command, "assert_task_valid", concurrent_validation)
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 75, result.output
    assert path.read_text() == newer.render()
    assert "owner 'zach'" not in _read_log(repo)


@pytest.mark.parametrize("status", ["in_progress", "blocked"])
def test_owner_stale_control_refuses_without_cli_sweep(git_repo, monkeypatch, status) -> None:
    from coga import cli

    cfg = load_config(git_repo.coga_os)
    ref = create_task(cfg=cfg, title="Stale owner", workflow_name="code",
                      contexts=[], owner="zach", agent="claude", status="paused")
    path = Path(ref["path"])
    git.sync_task_state(cfg, path, message="Seed ticket", strict=True)
    before = path.read_bytes()
    git_repo.checkout_branch("feature")
    newer = Ticket.read(path)
    newer.frontmatter["status"] = status
    newer.body += "\nNew control notes.\n"
    rel = str(path.relative_to(git_repo.root))
    # Leave origin/main stale: the first push must fail, fetch, and recheck.
    git_repo.push_competing_commit(rel, newer.render())
    monkeypatch.setattr("sys.argv", ["coga", "owner", ref["slug"], "marc"])
    sweeps = []
    monkeypatch.setattr(cli, "_sweep_coga_state", lambda cfg: sweeps.append(cfg))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 75
    assert not sweeps
    assert path.read_bytes() == before
    assert git_repo.git("show", f"main:{rel}", cwd=git_repo.origin) == newer.render()
    assert "owner 'zach'" not in _read_log(git_repo.coga_os)


@pytest.mark.parametrize("uncertain", [False, True])
def test_owner_publication_failure_rollback(repo: Path, monkeypatch, uncertain) -> None:
    from coga import git

    slug, path = _make_task(repo, status="paused")
    before = path.read_bytes()

    def fail(*args, **kwargs):
        assert kwargs["expect"] == {path: before}
        assert kwargs["strict"] is True
        if uncertain:
            raise git.UncertainPublishError("unreadable control")
        raise git.GitError("offline")

    monkeypatch.setattr(git, "sync_task_state", fail)
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 75
    assert Ticket.read(path).owner == ("marc" if uncertain else "zach")
    assert ("owner 'zach'" in _read_log(repo)) == uncertain


def test_owner_rollback_preserves_newer_local_edit(repo: Path, monkeypatch) -> None:
    from coga import git

    slug, path = _make_task(repo, status="paused")
    newer = Ticket.read(path)
    newer.body += "\nConcurrent editor.\n"

    def fail(*args, **kwargs):
        newer.write(path)
        raise git.StateRegressionError("control moved")

    monkeypatch.setattr(git, "sync_task_state", fail)
    result = CliRunner().invoke(app, ["owner", slug, "marc"])
    assert result.exit_code == 75
    assert path.read_text() == newer.render()
