from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from conftest import windows_skip

from conftest import seed_direct_body_workflow
from coga.authoring import (
    AuthoringError,
    finalize_authored,
    snapshot_authoring_state,
    validate_authored_task,
)
from coga.config import load_config
from coga.create import create_task
from coga.tasks import TaskRef, resolve_bootstrap, resolve_task
from coga.ticket import Ticket
from coga.validate import TaskValidationError


FINALIZE_SKILL = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "coga"
    / "resources"
    / "templates"
    / "coga"
    / "bootstrap"
    / "skills"
    / "coga"
    / "ticket"
    / "finalize"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [notification.slack]
        enabled = false
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        mode = "local"
        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    _write(
        coga_os / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        skills:
          - bootstrap/ticket
        ---

        ## Description

        Persistent launch target.
        """,
    )
    seed_direct_body_workflow(coga_os)
    monkeypatch.chdir(coga_os)
    return coga_os


def _create_task(
    repo: Path,
    title: str,
    *,
    workflow: str | None = "direct/body",
) -> TaskRef:
    cfg = load_config(repo)
    result = create_task(
        cfg=cfg,
        title=title,
        workflow_name=workflow,
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
    )
    return resolve_task(cfg, str(result["slug"]))


def test_validate_authored_task_rejects_workflowless_draft(repo: Path) -> None:
    cfg = load_config(repo)
    ref = _create_task(repo, "Workflowless draft", workflow=None)

    with pytest.raises(AuthoringError, match="no workflow"):
        validate_authored_task(cfg, ref)


def test_validate_authored_task_reports_schema_errors(repo: Path) -> None:
    cfg = load_config(repo)
    ref = _create_task(repo, "Broken authored task")
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["contexts"] = ["missing/context"]
    ticket.write(ref.ticket_path)

    with pytest.raises(TaskValidationError) as exc:
        validate_authored_task(cfg, ref)

    assert exc.value.action == "ticket authoring"
    assert "task validation failed after ticket authoring" in str(exc.value)
    assert "missing/context" in str(exc.value)


def test_ticket_finalize_skill_is_documentation_only() -> None:
    skill = (FINALIZE_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "name: coga/ticket/finalize" in skill
    assert "contexts/coga/git/SKILL.md" in skill
    assert not (FINALIZE_SKILL / "run.py").exists()


@pytest.mark.parametrize("edit_again", [False, True])
def test_finalize_authored_preserves_local_changes(
    git_repo, edit_again,
):
    repo = git_repo.coga_os
    cfg = load_config(repo)
    target = _create_task(repo, "Target")
    sibling = _create_task(repo, "Sibling")
    directory = sibling.path.with_suffix("")
    directory.mkdir()
    sibling.path.replace(directory / "ticket.md")
    sibling = resolve_task(cfg, sibling.id_slug)
    attachment = directory / "notes.txt"
    _write(attachment, "committed\n")
    git_repo.git("add", "coga/tasks")
    git_repo.git("commit", "-m", "seed tickets")
    git_repo.git("push", "origin", "main")
    _write(attachment, "pre-existing dirt\n")
    ticket = Ticket.read(target.ticket_path)
    ticket.body += "\nPre-existing target dirt.\n"
    ticket.write(target.ticket_path)
    before = snapshot_authoring_state(cfg)
    ticket = Ticket.read(sibling.ticket_path)
    ticket.body += "\nAuthored sibling handoff.\n"
    ticket.write(sibling.ticket_path)
    if edit_again:
        _write(attachment, "pre-existing dirt\nauthored addition\n")

    finalize_authored(cfg, before_snapshot=before, ref=target)

    def remote(path):
        return git_repo.git("show", f"main:{path.relative_to(git_repo.root).as_posix()}", cwd=git_repo.origin)

    assert "Authored sibling handoff." not in remote(sibling.ticket_path)
    assert "Authored sibling handoff." in sibling.ticket_path.read_text(encoding="utf-8")
    assert "Pre-existing target dirt." not in remote(target.ticket_path)
    assert "Pre-existing target dirt." in target.ticket_path.read_text(encoding="utf-8")
    assert remote(attachment) == "committed\n"
    assert "pre-existing dirt" in attachment.read_text(encoding="utf-8")


@pytest.mark.parametrize("bootstrap", [False, True])
@pytest.mark.parametrize("change", ["promotion", "deletion", "attachment_deletion"])
def test_finalize_authored_keeps_sibling_moves_and_removals_local(git_repo, bootstrap, change):
    import shutil

    cfg = load_config(git_repo.coga_os)
    target = _create_task(git_repo.coga_os, "Target")
    sibling = _create_task(git_repo.coga_os, "Sibling")
    directory = sibling.path.with_suffix("")
    attachment = directory / "notes.txt"
    if change != "promotion":
        directory.mkdir()
        sibling.path.replace(directory / "ticket.md")
        _write(attachment, "original\n")
    git_repo.git("add", "coga/tasks", "coga/log.md")
    git_repo.git("commit", "-m", "seed tickets")
    git_repo.git("push", "origin", "main")
    tip = git_repo.git("rev-parse", "main").strip()
    before = snapshot_authoring_state(cfg)
    if change == "promotion":
        directory.mkdir()
        sibling.path.replace(directory / "ticket.md")
        _write(attachment, "authored\n")
    elif change == "deletion":
        shutil.rmtree(directory)
    else:
        attachment.unlink()
    support = cfg.contexts_root / "team/SKILL.md"
    _write(support, "---\nname: team\ndescription: Team.\n---\nKnowledge.\n")

    finalize_authored(
        cfg, before_snapshot=before,
        ref=resolve_bootstrap(cfg, "ticket") if bootstrap else target,
    )

    assert git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip() == tip
    assert support.is_file()
    if change == "promotion":
        assert (directory / "ticket.md").is_file() and attachment.is_file()
    elif change == "deletion":
        assert not directory.exists()
    else:
        assert (directory / "ticket.md").is_file() and not attachment.exists()


def test_public_authoring_invocation_keeps_cli_argv_and_isolates_outer_session(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from coga.authoring import invoke_ticket_authoring
    from coga.task_env import TASK_ENV_KEYS
    import sys

    cfg = load_config(repo)
    created = create_task(cfg=cfg, title="Invocation boundary", workflow_name="direct/body", contexts=[], owner="marc", agent="claude", status="draft")
    ref = resolve_task(cfg, created["slug"])
    for key in TASK_ENV_KEYS:
        monkeypatch.setenv(key, "outer")
    monkeypatch.setenv("COGA_SUPERVISED", "1")
    monkeypatch.setenv("COGA_DONE_SENTINEL", "outer")
    def run(argv, *, cwd, env, defer_interrupt):
        assert argv == [sys.executable, "-c", "from coga.cli import main; main(existing_target_only=True)", "ticket", ref.id_slug, "--agent", "claude"]
        assert cwd == repo.parent and defer_interrupt
        assert not any(key in env for key in TASK_ENV_KEYS)
        assert "COGA_SUPERVISED" not in env and "COGA_DONE_SENTINEL" not in env
        return 75, False
    monkeypatch.setattr("coga.process_relay.run_foreground_child", run)
    assert invoke_ticket_authoring(cfg, ref, agent_name="claude") == 75


def test_authoring_invocation_refuses_a_vanished_pick_without_creating(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The queue's adapter never scaffolds a draft for a ref that moved away."""
    from coga.authoring import invoke_ticket_authoring
    from coga.tasks import list_tasks

    cfg = load_config(repo)
    created = create_task(cfg=cfg, title="Vanishing pick", workflow_name="direct/body", contexts=[], owner="marc", agent="claude", status="draft")
    ref = resolve_task(cfg, created["slug"])
    ref.ticket_path.unlink()
    before = sorted(t.id_slug for t in list_tasks(cfg))
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
    assert invoke_ticket_authoring(cfg, ref, agent_name="claude") == 2
    assert sorted(t.id_slug for t in list_tasks(load_config(repo))) == before
    assert not ref.ticket_path.exists()
