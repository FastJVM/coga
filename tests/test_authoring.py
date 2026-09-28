from __future__ import annotations

import subprocess
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


def test_finalize_authored_syncs_task_and_reports_support_paths(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
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

    calls: list[tuple[list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.publish",
        lambda cfg, paths, message: calls.append((list(paths), message)),
    )

    finalize_authored(cfg, before_snapshot=before, ref=ref)

    assert calls == [
        (
            [ref.path],
            "Ticket: sync-support — authored",
        )
    ]
    assert capsys.readouterr().err == (
        "[ticket] Coga did not publish these context/skill changes; "
        "carry them through a branch and human-reviewed PR:\n"
        f"  {context_path}\n  {skill_path}\n"
    )
    assert context_path.exists()
    assert skill_path.exists()


def test_finalize_authored_reports_relocated_contexts_dir(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout = repo.parent
    subprocess.run(
        ["git", "init", "-b", "main", str(checkout)],
        check=True, capture_output=True, text=True,
    )
    (checkout / "docs" / "contexts").mkdir(parents=True)
    (checkout / "docs" / "contexts" / ".gitkeep").write_text("")
    with (repo / "coga.toml").open("a") as f:
        f.write('[layout]\ncontexts = "docs/contexts"\n')

    cfg = load_config(repo)
    ref = _create_task(repo, "Relocated contexts")
    before = snapshot_authoring_state(cfg)

    context_path = checkout / "docs" / "contexts" / "team" / "note" / "SKILL.md"
    _write(
        context_path,
        """
        ---
        name: team/note
        description: note.
        ---
        """,
    )

    calls: list[tuple[list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.publish",
        lambda cfg, paths, message: calls.append((list(paths), message)),
    )

    finalize_authored(cfg, before_snapshot=before, ref=ref)

    assert calls == []
    assert str(context_path) in capsys.readouterr().err


def test_finalize_authored_skips_deleted_ticket(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
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

    calls: list[tuple[list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.publish",
        lambda cfg, paths, message: calls.append((list(paths), message)),
    )

    finalize_authored(cfg, before_snapshot=before, ref=ref)

    assert calls == []


def test_finalize_authored_re_resolves_file_task_promoted_for_attachment(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
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

    calls: list[tuple[list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.publish",
        lambda cfg, paths, message: calls.append((list(paths), message)),
    )

    finalize_authored(cfg, before_snapshot=before, ref=original_ref)

    assert calls == [
        (
            [original_ref.path, promoted_ref.path],
            "Ticket: promote-for-attachment — authored",
        )
    ]


def test_finalize_authored_discovers_new_task_from_bootstrap_interview(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = load_config(repo)
    before = snapshot_authoring_state(cfg)
    created_ref = _create_task(repo, "Fresh idea")
    bootstrap_ref = resolve_bootstrap(cfg, "ticket")

    calls: list[tuple[list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.publish",
        lambda cfg, paths, message: calls.append((list(paths), message)),
    )

    finalize_authored(cfg, before_snapshot=before, ref=bootstrap_ref)

    assert calls == [
        (
            [created_ref.path],
            "Ticket: fresh-idea — authored",
        )
    ]


def test_finalize_authored_reports_support_only_from_bootstrap_interview(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
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

    calls: list[tuple[list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.publish",
        lambda cfg, paths, message: calls.append((list(paths), message)),
    )

    finalize_authored(cfg, before_snapshot=before, ref=bootstrap_ref)

    assert calls == []
    assert str(context_path) in capsys.readouterr().err


def test_finalize_authored_reports_deleted_support_only(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
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

    calls: list[tuple[list[Path], str]] = []
    monkeypatch.setattr(
        "coga.authoring.git.publish",
        lambda cfg, paths, message: calls.append((list(paths), message)),
    )

    finalize_authored(cfg, before_snapshot=before, ref=bootstrap_ref)

    assert calls == []
    assert str(context_path) in capsys.readouterr().err


def test_ticket_finalize_skill_is_documentation_only() -> None:
    skill = (FINALIZE_SKILL / "SKILL.md").read_text()
    assert "name: coga/ticket/finalize" in skill
    assert "coga.authoring.finalize_authored" in skill
    assert not (FINALIZE_SKILL / "run.py").exists()


@pytest.mark.parametrize("launched", [False, True])
@pytest.mark.parametrize("change", ["new", "edited", "deleted", "unchanged"])
def test_finalize_authored_support_only_validates_unchanged_task(
    repo, monkeypatch, capsys, launched, change,
):
    cfg = load_config(repo)
    ref = _create_task(repo, "Unchanged task")
    if launched:
        monkeypatch.setenv("COGA_TASK_TICKET", str(ref.ticket_path))
        monkeypatch.setenv("COGA_TASK_SLUG", ref.id_slug)
    paths = [repo / kind / "team" / "SKILL.md" for kind in ("contexts", "skills")]
    if change != "new":
        for path in paths:
            _write(path, "original\n")
    before = snapshot_authoring_state(cfg)
    for path in paths:
        if change == "deleted":
            path.unlink()
        elif change != "unchanged":
            _write(path, "authored\n")
    validated = []

    def validate(cfg, ref):
        validated.append(ref)
        validate_authored_task(cfg, ref)

    monkeypatch.setattr("coga.authoring.validate_authored_task", validate)
    monkeypatch.setattr(
        "coga.authoring.git.publish",
        lambda *args: pytest.fail("unchanged task must not be published"),
    )
    finalize_authored(cfg, before_snapshot=before, ref=ref)
    assert validated == [ref]
    err = capsys.readouterr().err
    if change == "unchanged":
        assert err == ""
    else:
        assert "human-reviewed PR" in err
        assert [line.strip() for line in err.splitlines()[1:]] == list(map(str, paths))
    for path in paths:
        if change == "deleted":
            assert not path.exists()
        else:
            assert path.read_text() == ("original\n" if change == "unchanged" else "authored\n")


@pytest.mark.parametrize("failure", ["validation", "publication"])
def test_finalize_authored_reports_support_before_failure(repo, monkeypatch, capsys, failure):
    from coga import git

    cfg = load_config(repo)
    ref = _create_task(repo, "Failure")
    before = snapshot_authoring_state(cfg)
    context = repo / "contexts" / "team" / "SKILL.md"
    _write(context, "knowledge\n")
    ticket = Ticket.read(ref.ticket_path)
    ticket.body += "\nAuthored detail.\n"
    if failure == "validation":
        ticket.frontmatter["contexts"] = ["missing/context"]
    ticket.write(ref.ticket_path)

    def publish(*args):
        assert failure == "publication"
        assert str(context) in capsys.readouterr().err
        raise git.GitError("test push failure")

    monkeypatch.setattr("coga.authoring.git.publish", publish)
    if failure == "validation":
        with pytest.raises(TaskValidationError):
            finalize_authored(cfg, before_snapshot=before, ref=ref)
        assert str(context) in capsys.readouterr().err
    else:
        finalize_authored(cfg, before_snapshot=before, ref=ref)
        assert "[git] sync failed: test push failure" in capsys.readouterr().err
    assert context.read_text() == "knowledge\n"


@pytest.mark.parametrize("change", ["new", "edited", "deleted"])
def test_finalize_authored_publishes_attachment_changes(repo, monkeypatch, change):
    cfg = load_config(repo)
    ref = _create_task(repo, "Attachment")
    directory = ref.path.with_suffix("")
    directory.mkdir()
    ref.path.replace(directory / "ticket.md")
    ref = resolve_task(cfg, ref.id_slug)
    attachment = directory / "notes.txt"
    if change != "new":
        attachment.write_text("before\n")
    before = snapshot_authoring_state(cfg)
    if change == "deleted":
        attachment.unlink()
    else:
        attachment.write_text("after\n")
    calls = []
    monkeypatch.setattr("coga.authoring.git.publish", lambda cfg, paths, message: calls.append(paths))
    finalize_authored(cfg, before_snapshot=before, ref=ref)
    assert calls == [[ref.path]]


def test_finalize_authored_excludes_contexts_nested_in_task_directory(repo, monkeypatch, capsys):
    checkout = repo.parent
    subprocess.run(
        ["git", "init", "-b", "main", str(checkout)],
        check=True, capture_output=True, text=True,
    )
    ref = _create_task(repo, "Nested contexts")
    directory = ref.path.with_suffix("")
    directory.mkdir()
    ref.path.replace(directory / "ticket.md")
    (directory / "knowledge" / "team").mkdir(parents=True)
    context = directory / "knowledge" / "team" / "SKILL.md"
    context.write_text("before\n")
    rel = directory.relative_to(checkout).as_posix()
    with (repo / "coga.toml").open("a") as f:
        f.write(f'[layout]\ncontexts = "{rel}/knowledge"\n')
    cfg = load_config(repo)
    ref = resolve_task(cfg, ref.id_slug)
    attachment = directory / "notes.txt"
    before = snapshot_authoring_state(cfg)
    context.write_text("after\n")
    attachment.write_text("notes\n")
    calls = []
    monkeypatch.setattr("coga.authoring.git.publish", lambda cfg, paths, message: calls.append(paths))
    finalize_authored(cfg, before_snapshot=before, ref=ref)
    assert calls == [[attachment.resolve()]]
    assert str(context.resolve()) in capsys.readouterr().err
