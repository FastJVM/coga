"""Tests for `relay.git` — the git analogue of Slack sync (ticket A).

Covers config parsing of `[git]`, every branch of `sync_task_state`
(commit+push on the control branch, no-op on a feature branch / non-git /
disabled / nothing-staged, crash-loud on a failed push), and CLI integration
through the real-git `git_repo` fixture in conftest.

`git_repo` is the first real-git harness in the suite (git was fully mocked
before). B and C reuse it.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import typer
from typer.testing import CliRunner

from relay import git
from relay.cli import app
from relay.config import Config, ConfigError, load_config

runner = CliRunner()


# --- helpers -------------------------------------------------------------------


def _cfg(repo_root: Path, **over) -> Config:
    """Minimal Config for unit tests that only touch the git fields."""
    base: dict = dict(
        repo_root=repo_root,
        current_user="marc",
        default_status="draft",
        agents={},
        slack_webhook=None,
        slack_enabled=False,
        secrets={},
    )
    base.update(over)
    return Config(**base)


def _task_dir(parent: Path, slug: str = "demo") -> Path:
    """Create a task directory with a ticket file, return its path."""
    path = parent / "tasks" / slug
    path.mkdir(parents=True)
    (path / "ticket.md").write_text("---\ntitle: demo\n---\n\nbody\n")
    return path


def _write_config(tmp_path: Path, *, shared_extra: str = "", local_extra: str = "") -> Path:
    root = tmp_path / "relay-os"
    root.mkdir()
    (root / "relay.toml").write_text(f"version = 1\n{shared_extra}")
    (root / "relay.local.toml").write_text(f'user = "marc"\n{local_extra}')
    return root


# --- config parsing ------------------------------------------------------------


def test_git_config_defaults(tmp_path):
    cfg = load_config(_write_config(tmp_path))
    assert cfg.git_enabled is True
    assert cfg.git_remote == "origin"
    assert cfg.git_control_branch == "main"


def test_git_config_overrides(tmp_path):
    cfg = load_config(
        _write_config(
            tmp_path,
            shared_extra='[git]\nremote = "upstream"\ncontrol_branch = "trunk"\n',
        )
    )
    assert cfg.git_remote == "upstream"
    assert cfg.git_control_branch == "trunk"


def test_git_enabled_local_overrides_shared(tmp_path):
    cfg = load_config(
        _write_config(
            tmp_path,
            shared_extra="[git]\nenabled = true\n",
            local_extra="[git]\nenabled = false\n",
        )
    )
    assert cfg.git_enabled is False


def test_git_enabled_must_be_bool(tmp_path):
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_config(_write_config(tmp_path, shared_extra='[git]\nenabled = "yes"\n'))


def test_git_remote_must_be_nonempty(tmp_path):
    with pytest.raises(ConfigError, match="remote must be a non-empty string"):
        load_config(_write_config(tmp_path, shared_extra='[git]\nremote = ""\n'))


# --- sync_task_state branches --------------------------------------------------


def test_sync_commits_and_pushes_on_control_branch(git_repo):
    cfg = load_config(git_repo.relay_os)
    task = _task_dir(git_repo.relay_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert git_repo.origin_tracks("relay-os/tasks/demo/ticket.md")
    assert "Ticket: demo — created" in git_repo.origin_subjects()


def test_sync_scopes_commit_to_the_task_dir(git_repo):
    """An unrelated working-tree change is not swept into the task commit."""
    cfg = load_config(git_repo.relay_os)
    task = _task_dir(git_repo.relay_os)
    stray = git_repo.root / "STRAY.txt"
    stray.write_text("unrelated\n")

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert not git_repo.origin_tracks("STRAY.txt")
    # And it's still sitting uncommitted in the working tree.
    assert "STRAY.txt" in git_repo.git("status", "--porcelain")


def test_sync_does_not_commit_unrelated_staged_changes(git_repo):
    """A pre-staged unrelated change stays staged and is not pushed."""
    cfg = load_config(git_repo.relay_os)
    task = _task_dir(git_repo.relay_os)
    stray = git_repo.root / "STRAY.txt"
    stray.write_text("already staged by the user\n")
    git_repo.git("add", "STRAY.txt")

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert not git_repo.origin_tracks("STRAY.txt")
    assert "STRAY.txt" in git_repo.git("diff", "--cached", "--name-only")


def test_sync_noop_on_feature_branch(git_repo, capsys):
    cfg = load_config(git_repo.relay_os)
    git_repo.checkout_branch("feature/x")
    task = _task_dir(git_repo.relay_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    # Nothing landed on origin, and the task dir is still uncommitted.
    assert git_repo.origin_subjects() == ["init relay-os"]
    assert "tasks/" in git_repo.git("status", "--porcelain")
    assert "feature branch" in capsys.readouterr().err


def test_sync_noop_when_not_a_git_repo(tmp_path, capsys, real_git):
    cfg = _cfg(tmp_path)
    task = _task_dir(tmp_path)

    # Must not raise — a non-git relay-os checkout is a soft no-op.
    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "not a git repo" in capsys.readouterr().err


def test_sync_crashes_loud_on_rev_parse_failure(tmp_path, monkeypatch, real_git):
    cfg = _cfg(tmp_path)
    task = _task_dir(tmp_path)

    class Result:
        returncode = 128
        stdout = ""
        stderr = "fatal: detected dubious ownership in repository"

    monkeypatch.setattr(git.subprocess, "run", lambda *a, **k: Result())

    with pytest.raises(typer.Exit):
        git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "sync failed" in (task / "log.md").read_text()


def test_sync_suppressed_when_disabled(tmp_path, capsys, real_git):
    cfg = _cfg(tmp_path, git_enabled=False)
    task = _task_dir(tmp_path)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "disabled" in capsys.readouterr().err


def test_sync_noop_when_nothing_changed(git_repo):
    cfg = load_config(git_repo.relay_os)
    task = _task_dir(git_repo.relay_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")
    before = git_repo.origin_subjects()
    # Second call: the files are already committed and unchanged → nothing
    # staged → no second commit, no push.
    git.sync_task_state(cfg, task, message="Ticket: demo — again")

    assert git_repo.origin_subjects() == before


def test_sync_crashes_loud_on_push_failure(git_repo):
    """Crash-loud (owner decision): a failed push raises typer.Exit and logs."""
    cfg = load_config(git_repo.relay_os)
    git_repo.git("remote", "remove", "origin")
    task = _task_dir(git_repo.relay_os)

    with pytest.raises(typer.Exit):
        git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "sync failed" in (task / "log.md").read_text()


# --- CLI integration through real git ------------------------------------------


def test_cli_draft_then_activate_sync_to_origin(git_repo):
    result = runner.invoke(app, ["draft", "Demo task", "--workflow", "code"])
    assert result.exit_code == 0, result.output
    slug = result.output.split(":", 1)[0].strip()

    activated = runner.invoke(app, ["mark", "active", slug])
    assert activated.exit_code == 0, activated.output

    subjects = git_repo.origin_subjects()
    assert f"Ticket: {slug} — created" in subjects
    assert f"Ticket: {slug} — active" in subjects
    assert git_repo.origin_tracks(f"relay-os/tasks/{slug}/ticket.md")


def test_cli_bump_syncs_step_to_origin(git_repo):
    result = runner.invoke(app, ["draft", "Demo task", "--workflow", "code"])
    slug = result.output.split(":", 1)[0].strip()
    runner.invoke(app, ["mark", "active", slug])

    # Move to in_progress by hand (launch normally does this, but it spawns an
    # agent). The hand edit is swept into the bump's commit — fine for the test.
    ticket = git_repo.relay_os / "tasks" / slug / "ticket.md"
    ticket.write_text(ticket.read_text().replace("status: active", "status: in_progress"))

    bumped = runner.invoke(app, ["bump", slug])
    assert bumped.exit_code == 0, bumped.output

    assert any(
        s.startswith(f"Ticket: {slug} — step 2 (review)")
        for s in git_repo.origin_subjects()
    )
