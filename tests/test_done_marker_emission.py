"""Tests for the session-done signal on session-ending commands.

`coga bump`, `coga mark done`, `coga mark canceled`, and `coga block` signal
the supervising
`coga launch` that the session is over so it can SIGTERM the agent's REPL
(see `coga.repl_supervisor`). The signal travels over the *sentinel file*
(`$COGA_DONE_SENTINEL`) and nothing else: a success writes the task's
`id_slug` into the file, scoped to this session. The slug (not the resolved
path) is what makes the signal survive a bump run from a different checkout
of the repo, where the same ticket lives at two absolute paths. Other
transitions (`mark active`, `mark paused`, or any error path) must NOT write
it at all — the
session is not over.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.repl_supervisor import SENTINEL_ENV
from coga.create import create_task


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
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
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
          - name: pr
          - name: merge
        ---
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(
    repo: Path, *, workflow: str | None = "code", status: str = "in_progress"
) -> tuple[str, Path]:
    cfg = load_config(repo)
    if workflow is None and status != "draft":
        # `create_task` refuses to create a workflow-less non-draft task now,
        # so the workflow-less bump-error test constructs that shape on disk.
        return _write_workflow_less_task(repo, status=status)
    ref = create_task(
        cfg=cfg, title="Work", workflow_name=workflow,
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status=status,
    )
    return ref["slug"], ref["path"]


def _write_workflow_less_task(
    repo: Path, *, slug: str = "work", status: str = "in_progress"
) -> tuple[str, Path]:
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        slug: {slug}
        title: Work
        status: {status}
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: null
        ---

        ## Description

        <!-- coga:blackboard -->
        # Blackboard
    """).lstrip())
    return slug, task_dir


@pytest.fixture
def sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pretend a `coga launch` supervisor is watching: advertise the sentinel
    file path the way `run_with_done_marker` does for its child."""
    path = tmp_path / "coga-done" / "sentinel"
    path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(SENTINEL_ENV, str(path))
    return path


def _no_supervisor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SENTINEL_ENV, raising=False)


# --- bump ---------------------------------------------------------------------


def test_bump_success_signals_via_sentinel(
    repo: Path, sentinel: Path
) -> None:
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    # The signal goes to the side-channel file, scoped to this task by its
    # checkout-independent `id_slug` (not the resolved path).
    assert sentinel.read_text().strip() == slug


def test_bump_success_unsupervised_is_noop(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No supervisor (no env var): the signal is a silent no-op rather than an
    error — there is no in-band channel to fall back to."""
    _no_supervisor(monkeypatch)
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output


def test_bump_error_past_final_step_does_not_signal(
    repo: Path, sentinel: Path
) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])  # → step 2
    runner.invoke(app, ["bump", slug])  # → step 3 (final), signals success
    # Clear the sentinel left by the successful bumps so the assertion below
    # isolates the *erroring* bump's behavior.
    sentinel.unlink(missing_ok=True)
    result = runner.invoke(app, ["bump", slug])  # past final
    assert result.exit_code == 2
    assert not sentinel.exists()


def test_bump_error_no_workflow_does_not_signal(
    repo: Path, sentinel: Path
) -> None:
    slug, _ = _make_task(repo, workflow=None)
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 2
    assert not sentinel.exists()


def test_bump_error_wrong_status_does_not_signal(
    repo: Path, sentinel: Path
) -> None:
    slug, _ = _make_task(repo, status="paused")
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 2
    assert not sentinel.exists()


# --- mark done ----------------------------------------------------------------


def test_mark_done_success_signals_via_sentinel(
    repo: Path, sentinel: Path
) -> None:
    slug, _ = _make_task(repo, status="active")
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert sentinel.read_text().strip() == slug


def test_mark_done_success_unsupervised_is_noop(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_supervisor(monkeypatch)
    slug, _ = _make_task(repo, status="active")
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output


def test_mark_done_error_does_not_signal(repo: Path, sentinel: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 2
    assert not sentinel.exists()


def test_mark_canceled_success_signals_via_sentinel(
    repo: Path, sentinel: Path
) -> None:
    slug, _ = _make_task(repo, status="active")
    result = CliRunner().invoke(
        app, ["mark", "canceled", slug, "--message", "Owner declined"]
    )
    assert result.exit_code == 0, result.output
    assert sentinel.read_text().strip() == slug


def test_mark_canceled_error_does_not_signal(repo: Path, sentinel: Path) -> None:
    slug, _ = _make_task(repo, status="active")
    result = CliRunner().invoke(
        app, ["mark", "canceled", slug, "--message", "   "]
    )
    assert result.exit_code == 2
    assert not sentinel.exists()


def test_mark_active_does_not_signal(repo: Path, sentinel: Path) -> None:
    """Non-terminal mark transitions do not signal session end."""
    slug, _ = _make_task(repo, status="draft")
    result = CliRunner().invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    assert not sentinel.exists()


def test_mark_paused_does_not_signal(repo: Path, sentinel: Path) -> None:
    slug, _ = _make_task(repo, status="active")
    result = CliRunner().invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 0, result.output
    assert not sentinel.exists()


# --- block --------------------------------------------------------------------


def test_block_success_signals_via_sentinel(
    repo: Path, sentinel: Path
) -> None:
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(
        app, ["block", "--task", slug, "--reason", "stuck on 429 backoff ceiling"]
    )
    assert result.exit_code == 0, result.output
    assert sentinel.read_text().strip() == slug


def test_block_success_unsupervised_is_noop(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_supervisor(monkeypatch)
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(
        app, ["block", "--task", slug, "--reason", "stuck on 429 backoff ceiling"]
    )
    assert result.exit_code == 0, result.output


def test_block_error_empty_reason_does_not_signal(
    repo: Path, sentinel: Path
) -> None:
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(
        app, ["block", "--task", slug, "--reason", "   "]
    )
    assert result.exit_code == 2
    assert not sentinel.exists()


# --- checkout-independence (the regression this fix closes) -------------------


def test_sentinel_scope_is_checkout_independent(repo: Path) -> None:
    """The sentinel is scoped by `id_slug`, not the resolved path.

    The supervisor may scope the channel from one checkout while the agent's
    `coga bump` runs in another (e.g. a peer agent's separate clone) — two
    different absolute paths for one ticket. A path-scoped marker written from
    the "wrong" checkout never matched what the supervisor polled, so the REPL
    hung and the human had to relaunch by hand. `id_slug` is the same from
    either checkout, so the two sides agree.

    This asserts the invariant the fix relies on: the identity string is stable
    across checkouts, while the resolved path — the OLD scope key — is not.
    """
    from coga import tasks as tasks_mod

    slug, primary_path = _make_task(repo)

    # Mirror the whole task tree into a second checkout of the same repo.
    import shutil

    wt_root = repo.parent / "second-checkout"
    shutil.copytree(repo, wt_root)

    primary_ref = tasks_mod.resolve_target(load_config(repo), slug)
    worktree_ref = tasks_mod.resolve_target(load_config(wt_root), slug)

    # What `launch` scopes to and what `bump`/`mark`/`block` write — identical
    # from either checkout. This is what makes teardown fire regardless of the
    # bump's cwd.
    assert primary_ref.id_slug == worktree_ref.id_slug == slug

    # The resolved paths (the pre-fix scope key) genuinely diverge — that
    # divergence is exactly the mismatch that used to hang the REPL.
    assert primary_ref.path.resolve() != worktree_ref.path.resolve()
    assert primary_ref.path.resolve() == primary_path.resolve()
