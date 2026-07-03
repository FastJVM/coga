from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from conftest import seed_direct_body_workflow
from coga.authoring import (
    AUTHORING_REF_ENV,
    AUTHORING_SNAPSHOT_ENV,
    AuthoringError,
    finalize_authored,
    finalize_authored_from_env,
    snapshot_authoring_state,
    validate_authored_task,
    write_authoring_snapshot,
)
from coga.config import load_config
from coga.create import create_task
from coga.tasks import TaskRef, resolve_bootstrap, resolve_task
from coga.ticket import Ticket


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
        mode: agent
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
        mode="agent",
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

    with pytest.raises(AuthoringError) as exc:
        validate_authored_task(cfg, ref)

    assert "Ticket validation failed after authoring" in str(exc.value)
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


def test_finalize_authored_from_env_reads_snapshot(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = load_config(repo)
    ref = _create_task(repo, "Env finalize")
    before = snapshot_authoring_state(cfg)
    snapshot_path = tmp_path / "authoring-snapshot.json"
    write_authoring_snapshot(before, snapshot_path)

    ticket = Ticket.read(ref.ticket_path)
    ticket.body += "\n\nAuthored through env finalize.\n"
    ticket.write(ref.ticket_path)

    calls: list[str] = []
    monkeypatch.setattr(
        "coga.authoring.git.sync_paths",
        lambda cfg, anchor, paths, *, message: calls.append(message),
    )

    finalize_authored_from_env(
        cfg,
        {
            AUTHORING_REF_ENV: ref.id_slug,
            AUTHORING_SNAPSHOT_ENV: str(snapshot_path),
        },
    )

    assert calls == ["Ticket: env-finalize — authored"]


def _load_finalize_script():
    spec = importlib.util.spec_from_file_location(
        "ticket_finalize_skill", FINALIZE_SKILL / "run.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ticket_finalize_skill_declares_script_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = (FINALIZE_SKILL / "SKILL.md").read_text()
    assert "name: coga/ticket/finalize" in skill
    assert "script: run.py" in skill

    module = _load_finalize_script()
    called = False

    def fake_finalize() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(module, "finalize_authored_from_env", fake_finalize)

    assert module.main() == 0
    assert called is True
