from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

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
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
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
        assignee: claude
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
        assignee="claude",
        watchers=[],
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


def test_finalize_authored_syncs_task_and_support_paths(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    ref = _create_task(repo, "Sync support")
    before = snapshot_authoring_state(cfg)

    ticket = Ticket.read(ref.ticket_path)
    ticket.body += "\n\nAuthored detail.\n"
    ticket.write(ref.ticket_path)
    context_path = repo / "contexts" / "team" / "note" / "SKILL.md"
    _write(
        context_path,
        """
        ---
        name: team/note
        description: note.
        ---
        """,
    )
    skill_path = repo / "skills" / "team" / "helper" / "SKILL.md"
    _write(
        skill_path,
        """
        ---
        name: team/helper
        description: helper.
        ---
        """,
    )

    calls: list[tuple[Path, list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.sync_paths",
        lambda cfg, anchor, paths, *, message: calls.append(
            (anchor, list(paths), message)
        ),
    )

    finalize_authored(cfg, before_snapshot=before, ref=ref)

    assert calls == [
        (
            ref.path,
            [ref.path, context_path, skill_path],
            "Ticket: sync-support — authored",
        )
    ]


def test_finalize_authored_skips_deleted_ticket(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A session may end by deleting the ticket (the human decides the task
    # should go away). `finalize_authored` must not fail validating a ref
    # whose ticket.md was removed, nor try to re-sync it.
    import shutil

    cfg = load_config(repo)
    ref = _create_task(repo, "Delete me")
    before = snapshot_authoring_state(cfg)

    if ref.path.is_dir():
        shutil.rmtree(ref.path)
    else:
        ref.path.unlink()

    calls: list[tuple[Path, list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.sync_paths",
        lambda cfg, anchor, paths, *, message: calls.append(
            (anchor, list(paths), message)
        ),
    )

    finalize_authored(cfg, before_snapshot=before, ref=ref)

    assert calls == []


def test_finalize_authored_re_resolves_file_task_promoted_for_attachment(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    original_ref = _create_task(repo, "Promote for attachment")
    assert original_ref.file_form is True
    before = snapshot_authoring_state(cfg)

    promoted_dir = original_ref.path.with_suffix("")
    promoted_dir.mkdir()
    promoted_ticket = promoted_dir / "ticket.md"
    original_ref.path.replace(promoted_ticket)
    (promoted_dir / "notes.txt").write_text("supporting material\n")

    promoted_ref = resolve_task(cfg, original_ref.id_slug)
    assert promoted_ref.file_form is False

    calls: list[tuple[Path, list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.sync_paths",
        lambda cfg, anchor, paths, *, message: calls.append(
            (anchor, list(paths), message)
        ),
    )

    finalize_authored(cfg, before_snapshot=before, ref=original_ref)

    assert calls == [
        (
            promoted_ref.path,
            [original_ref.path, promoted_ref.path],
            "Ticket: promote-for-attachment — authored",
        )
    ]


def test_finalize_authored_discovers_new_task_from_bootstrap_interview(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    before = snapshot_authoring_state(cfg)
    created_ref = _create_task(repo, "Fresh idea")
    bootstrap_ref = resolve_bootstrap(cfg, "ticket")

    calls: list[tuple[Path, list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.sync_paths",
        lambda cfg, anchor, paths, *, message: calls.append(
            (anchor, list(paths), message)
        ),
    )

    finalize_authored(cfg, before_snapshot=before, ref=bootstrap_ref)

    assert calls == [
        (
            created_ref.path,
            [created_ref.path],
            "Ticket: fresh-idea — authored",
        )
    ]


def test_finalize_authored_syncs_support_only_from_bootstrap_interview(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    before = snapshot_authoring_state(cfg)
    context_path = repo / "contexts" / "team" / "note" / "SKILL.md"
    _write(
        context_path,
        """
        ---
        name: team/note
        description: note.
        ---
        """,
    )
    bootstrap_ref = resolve_bootstrap(cfg, "ticket")

    calls: list[tuple[Path, list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.sync_paths",
        lambda cfg, anchor, paths, *, message: calls.append(
            (anchor, list(paths), message)
        ),
    )

    finalize_authored(cfg, before_snapshot=before, ref=bootstrap_ref)

    assert calls == [
        (
            repo,
            [context_path],
            "Ticket authoring — support files",
        )
    ]


def test_finalize_authored_syncs_deleted_support_only_with_live_anchor(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    context_path = repo / "contexts" / "team" / "note" / "SKILL.md"
    _write(
        context_path,
        """
        ---
        name: team/note
        description: note.
        ---
        """,
    )
    before = snapshot_authoring_state(cfg)
    context_path.unlink()
    bootstrap_ref = resolve_bootstrap(cfg, "ticket")

    calls: list[tuple[Path, list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.sync_paths",
        lambda cfg, anchor, paths, *, message: calls.append(
            (anchor, list(paths), message)
        ),
    )

    finalize_authored(cfg, before_snapshot=before, ref=bootstrap_ref)

    assert calls == [
        (
            repo,
            [context_path],
            "Ticket authoring — support files",
        )
    ]


def test_ticket_finalize_skill_is_documentation_only() -> None:
    skill = (FINALIZE_SKILL / "SKILL.md").read_text()
    assert "name: coga/ticket/finalize" in skill
    assert "coga.authoring.finalize_authored" in skill
    assert not (FINALIZE_SKILL / "run.py").exists()
