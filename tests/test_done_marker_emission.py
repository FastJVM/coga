"""Tests for the session-done signal on session-ending commands.

`relay bump`, `relay mark done`, and `relay panic` signal the supervising
`relay launch` that the session is over so it can SIGTERM the agent's REPL
(see `relay.repl_supervisor`). The signal travels over the *sentinel file*
(`$RELAY_DONE_SENTINEL`), not stdout: the raw `DONE_MARKER` must never leak
into the command's visible output, or a TUI shows it to the human and it can
cross-talk into a parent supervisor's PTY. Other transitions (`mark active`,
`mark paused`, or any error path) must NOT signal at all — the session is
not over.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.repl_supervisor import DONE_MARKER, SENTINEL_ENV
from relay.scaffold import scaffold_task


_MARKER = DONE_MARKER.decode("ascii")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
    ref = scaffold_task(
        cfg=cfg, title="Work", workflow_name=workflow,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status=status,
    )
    return ref["slug"], ref["path"]


@pytest.fixture
def sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pretend a `relay launch` supervisor is watching: advertise the sentinel
    file path the way `run_with_done_marker` does for its child."""
    path = tmp_path / "relay-done" / "sentinel"
    path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(SENTINEL_ENV, str(path))
    return path


def _no_supervisor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SENTINEL_ENV, raising=False)


# --- bump ---------------------------------------------------------------------


def test_bump_success_signals_via_sentinel_not_stdout(
    repo: Path, sentinel: Path
) -> None:
    slug, path = _make_task(repo)
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    # The signal goes to the side-channel file, scoped to this task...
    assert sentinel.read_text().strip() == str(path.resolve())
    # ...and never leaks the raw marker into visible output.
    assert _MARKER not in result.output


def test_bump_success_unsupervised_does_not_leak_marker(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No supervisor (no env var): nothing watches for the marker, so it must
    not be printed into the human's transcript."""
    _no_supervisor(monkeypatch)
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    assert _MARKER not in result.output


def test_bump_error_past_final_step_does_not_emit_marker(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])  # → step 2
    runner.invoke(app, ["bump", slug])  # → step 3 (final)
    result = runner.invoke(app, ["bump", slug])  # past final
    assert result.exit_code == 2
    assert _MARKER not in result.output


def test_bump_error_no_workflow_does_not_emit_marker(repo: Path) -> None:
    slug, _ = _make_task(repo, workflow=None)
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 2
    assert _MARKER not in result.output


def test_bump_error_wrong_status_does_not_emit_marker(repo: Path) -> None:
    slug, _ = _make_task(repo, status="paused")
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 2
    assert _MARKER not in result.output


# --- mark done ----------------------------------------------------------------


def test_mark_done_success_signals_via_sentinel_not_stdout(
    repo: Path, sentinel: Path
) -> None:
    slug, path = _make_task(repo, status="active")
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert sentinel.read_text().strip() == str(path.resolve())
    assert _MARKER not in result.output


def test_mark_done_success_unsupervised_does_not_leak_marker(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_supervisor(monkeypatch)
    slug, _ = _make_task(repo, status="active")
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert _MARKER not in result.output


def test_mark_done_error_does_not_emit_marker(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 2
    assert _MARKER not in result.output


def test_mark_active_does_not_emit_marker(repo: Path) -> None:
    """Only the terminal `mark done` transition signals session end."""
    slug, _ = _make_task(repo, status="draft")
    result = CliRunner().invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    assert _MARKER not in result.output


def test_mark_paused_does_not_emit_marker(repo: Path) -> None:
    slug, _ = _make_task(repo, status="active")
    result = CliRunner().invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 0, result.output
    assert _MARKER not in result.output


# --- panic --------------------------------------------------------------------


def test_panic_success_signals_via_sentinel_not_stdout(
    repo: Path, sentinel: Path
) -> None:
    slug, path = _make_task(repo)
    result = CliRunner().invoke(
        app, ["panic", "--task", slug, "--reason", "stuck on 429 backoff ceiling"]
    )
    # Panic exits non-zero on the success path; the supervisor is still
    # released — via the sentinel file, not a visible marker.
    assert result.exit_code == 1, result.output
    assert sentinel.read_text().strip() == str(path.resolve())
    assert _MARKER not in result.output


def test_panic_success_unsupervised_does_not_leak_marker(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_supervisor(monkeypatch)
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(
        app, ["panic", "--task", slug, "--reason", "stuck on 429 backoff ceiling"]
    )
    assert result.exit_code == 1, result.output
    assert _MARKER not in result.output


def test_panic_error_empty_reason_does_not_emit_marker(repo: Path) -> None:
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(
        app, ["panic", "--task", slug, "--reason", "   "]
    )
    assert result.exit_code == 2
    assert _MARKER not in result.output
