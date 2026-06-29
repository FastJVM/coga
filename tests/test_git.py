"""Tests for `coga.git` — the git analogue of Slack sync (ticket A).

Covers config parsing of `[git]`, every branch of `sync_task_state`
(commit+push on the control branch, no-op on a feature branch / non-git /
disabled / nothing-staged, crash-loud on a failed push), and CLI integration
through the real-git `git_repo` fixture in conftest.

`git_repo` is the first real-git harness in the suite (git was fully mocked
before). B and C reuse it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga import git
from coga.cli import app
from coga.config import Config, ConfigError, load_config
from coga.logfile import append_log
from coga.ticket import Ticket

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
    )
    base.update(over)
    return Config(**base)


def _global_log(cfg: Config) -> str:
    """Read the repo-global audit log (`coga/log.md`) where sync failures
    are now recorded (the per-task `log.md` is gone in the single-file format)."""
    log = cfg.repo_root / "log.md"
    return log.read_text() if log.is_file() else ""


def _task_dir(parent: Path, slug: str = "demo") -> Path:
    """Create a task directory with a ticket file, return its path."""
    path = parent / "tasks" / slug
    path.mkdir(parents=True)
    (path / "ticket.md").write_text("---\ntitle: demo\n---\n\nbody\n")
    return path


def _write_config(tmp_path: Path, *, shared_extra: str = "", local_extra: str = "") -> Path:
    root = tmp_path / "coga"
    root.mkdir()
    (root / "coga.toml").write_text(f"version = 1\n{shared_extra}")
    (root / "coga.local.toml").write_text(f'user = "marc"\n{local_extra}')
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
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    assert "Ticket: demo — created" in git_repo.origin_subjects()


def test_sync_scopes_commit_to_the_task_dir(git_repo):
    """An unrelated working-tree change is not swept into the task commit."""
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)
    stray = git_repo.root / "STRAY.txt"
    stray.write_text("unrelated\n")

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert not git_repo.origin_tracks("STRAY.txt")
    # And it's still sitting uncommitted in the working tree.
    assert "STRAY.txt" in git_repo.git("status", "--porcelain")


def test_sync_does_not_commit_unrelated_staged_changes(git_repo):
    """A pre-staged unrelated change stays staged and is not pushed."""
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)
    stray = git_repo.root / "STRAY.txt"
    stray.write_text("already staged by the user\n")
    git_repo.git("add", "STRAY.txt")

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert not git_repo.origin_tracks("STRAY.txt")
    assert "STRAY.txt" in git_repo.git("diff", "--cached", "--name-only")


def test_sync_lands_on_main_from_feature_branch(git_repo):
    """From a feature branch, task state lands on origin/main AND on HEAD."""
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    task = _task_dir(git_repo.coga_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    # Landed on the shared control branch...
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    assert "Ticket: demo — created" in git_repo.origin_subjects()
    # ...and committed on the feature branch (clean tree, reflects ticket state).
    assert "tasks/" not in git_repo.git("status", "--porcelain")
    assert "Ticket: demo — created" in git_repo.git("log", "--format=%s", "feature/x")
    # The control branch was never checked out.
    assert git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "feature/x"


# --- sync_log branches ---------------------------------------------------------


def test_sync_log_commits_and_pushes_the_log_on_control_branch(git_repo):
    """A bare log append is committed + pushed, never left dirty (the bootstrap
    launch hole that blocks the next `git pull` at the checkout gate)."""
    cfg = load_config(git_repo.coga_os)
    append_log(cfg, "bootstrap/orient", "human:nick", "launched in interactive mode")
    # The append starts life uncommitted in the working tree.
    assert "log.md" in git_repo.git("status", "--porcelain")

    git.sync_log(cfg, message="Log: bootstrap/orient")

    # Committed (clean tree) and pushed to the shared control branch.
    assert "log.md" not in git_repo.git("status", "--porcelain")
    assert git_repo.origin_tracks("coga/log.md")
    assert "Log: bootstrap/orient" in git_repo.origin_subjects()


def test_sync_log_scopes_commit_to_the_log_only(git_repo):
    """An unrelated dirty file is not swept into the log commit."""
    cfg = load_config(git_repo.coga_os)
    append_log(cfg, "bootstrap/orient", "human:nick", "launched")
    stray = git_repo.root / "STRAY.txt"
    stray.write_text("unrelated\n")

    git.sync_log(cfg, message="Log: bootstrap/orient")

    assert not git_repo.origin_tracks("STRAY.txt")
    assert "STRAY.txt" in git_repo.git("status", "--porcelain")


def test_sync_log_commits_locally_only_on_feature_branch(git_repo):
    """On a feature branch the log is committed locally (not dirty) but never
    overlaid onto the control branch — it reaches it union-safely via PR merge."""
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    append_log(cfg, "bootstrap/orient", "human:nick", "launched")

    git.sync_log(cfg, message="Log: bootstrap/orient")

    assert "log.md" not in git_repo.git("status", "--porcelain")
    assert "Log: bootstrap/orient" in git_repo.git("log", "--format=%s", "feature/x")
    # Not landed on the control branch (no overlay that could clobber appends).
    assert not git_repo.origin_tracks("coga/log.md")
    assert git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "feature/x"


def test_sync_log_failure_does_not_redirty_the_log(git_repo, capsys):
    """A failed log sync surfaces to stderr but does NOT append to log.md —
    re-dirtying the file it failed to commit would recreate the dangling line."""
    cfg = load_config(git_repo.coga_os)
    git_repo.git("remote", "remove", "origin")
    append_log(cfg, "bootstrap/orient", "human:nick", "launched")
    before = (cfg.repo_root / "log.md").read_text()

    # Must not raise.
    git.sync_log(cfg, message="Log: bootstrap/orient")

    # The log content is unchanged (no `[git] sync failed` line appended)...
    assert (cfg.repo_root / "log.md").read_text() == before
    # ...and the miss is surfaced loudly instead.
    assert "log sync failed" in capsys.readouterr().err


def test_sync_feature_branch_relands_existing_task_after_local_change(git_repo):
    """Regression: cross-branch land of a task that ALREADY exists on main.

    The overlay-tree builder seeds a temp index from origin/main (which already
    holds the task), then `git rm --cached` the task subtree. Before the `-rf`
    fix that `rm` refused — the temp-index content differed from both the
    working file and the feature HEAD (which the local commit had just moved),
    tripping git's "staged content differs" guard — so the land crashed. This
    is the common `coga panic` / re-author case: the ticket was created on a
    prior run, then edited again from a feature worktree.
    """
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)

    # First land: the task now exists on origin/main (created on an earlier run).
    git.sync_task_state(cfg, task, message="Ticket: demo — created")
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")

    # Now, from a feature branch, change the task and sync again.
    git_repo.checkout_branch("feature/x")
    (task / "blackboard.md").write_text("## Blockers\n\nstuck\n")

    git.sync_task_state(cfg, task, message="Ticket: demo — panic")

    assert "Ticket: demo — panic" in git_repo.origin_subjects()
    assert git_repo.origin_tracks("coga/tasks/demo/blackboard.md")
    landed = git_repo.git(
        "show", "main:coga/tasks/demo/blackboard.md", cwd=git_repo.origin
    )
    assert "stuck" in landed


def test_sync_feature_branch_leaves_working_tree_untouched(git_repo):
    """Pre-existing staged + unstaged code edits survive a cross-branch land."""
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    task = _task_dir(git_repo.coga_os)

    # An unstaged edit and a separately staged edit, both outside the task dir.
    unstaged = git_repo.root / "UNSTAGED.txt"
    unstaged.write_text("dirty unstaged\n")
    staged = git_repo.root / "STAGED.txt"
    staged.write_text("dirty staged\n")
    git_repo.git("add", "STAGED.txt")

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    porcelain = git_repo.git("status", "--porcelain")
    # Unstaged stays unstaged; staged stays staged; neither was pushed.
    assert "?? UNSTAGED.txt" in porcelain
    assert "A  STAGED.txt" in porcelain
    assert not git_repo.origin_tracks("UNSTAGED.txt")
    assert not git_repo.origin_tracks("STAGED.txt")
    # Neither file is on the feature branch HEAD commit either.
    assert "STAGED.txt" not in git_repo.git("ls-tree", "-r", "--name-only", "HEAD")


def test_sync_feature_branch_retries_on_non_fast_forward(git_repo):
    """A competing push to origin/main is absorbed by the retry loop, not clobbered."""
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    task = _task_dir(git_repo.coga_os)

    # Another process lands an unrelated file on origin/main first.
    git_repo.push_competing_commit("RIVAL.txt", "landed first\n")

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    # Both the competing file and our task file are on origin/main — anti-clobber.
    assert git_repo.origin_tracks("RIVAL.txt")
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    subjects = git_repo.origin_subjects()
    assert "Ticket: demo — created" in subjects
    assert "competing: RIVAL.txt" in subjects


def test_sync_feature_branch_retry_loop_survives_mid_flight_race(git_repo, monkeypatch):
    """Force a non-ff *between* fetch and push: the loop refetches and succeeds.

    `push_competing_commit` before the call (above) may land as a clean
    fast-forward because we fetch the latest tip first. To actually exercise
    the retry branch, inject a competing commit on the first push attempt — so
    our push is rejected non-ff — then let the second attempt go through.
    """
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    task = _task_dir(git_repo.coga_os)

    real_push = git._push_ref
    calls = {"n": 0}

    def racing_push(root, remote, refspec):
        calls["n"] += 1
        if calls["n"] == 1:
            # A rival lands first, after we already fetched — our push is non-ff.
            git_repo.push_competing_commit("RIVAL.txt", "raced in\n")
        return real_push(root, remote, refspec)

    monkeypatch.setattr(git, "_push_ref", racing_push)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert calls["n"] >= 2  # first push rejected, retried
    assert git_repo.origin_tracks("RIVAL.txt")
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")


def test_sync_feature_branch_noop_when_identical(git_repo):
    """No second land when origin/main already has identical task content."""
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    task = _task_dir(git_repo.coga_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")
    before = git_repo.origin_subjects()
    # Re-run with no task-file change: HEAD commit is a no-op (nothing staged)
    # and the overlay tree matches origin/main's tree, so no new land.
    git.sync_task_state(cfg, task, message="Ticket: demo — again")

    assert git_repo.origin_subjects() == before


def test_sync_feature_branch_nonfatal_on_push_failure(git_repo, capsys):
    """No remote on the cross-branch path → loud warning + log, but no crash.

    A failed push must not abort a local state transition (it would break the
    supervised launch chain). The miss is surfaced to stderr + log.md.
    """
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    git_repo.git("remote", "remove", "origin")
    task = _task_dir(git_repo.coga_os)

    # Must not raise.
    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "sync failed" in capsys.readouterr().err
    assert "sync failed" in _global_log(cfg)


def test_sync_detached_head_lands_without_local_commit(git_repo, capsys):
    """Detached HEAD: still lands on main, skips the (orphan-ish) local commit."""
    cfg = load_config(git_repo.coga_os)
    git_repo.git("checkout", "--detach", "HEAD")
    task = _task_dir(git_repo.coga_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    # No local commit was made — the task dir is still uncommitted on disk.
    assert "tasks/" in git_repo.git("status", "--porcelain")
    assert "detached HEAD" in capsys.readouterr().err


def test_sync_noop_when_not_a_git_repo(tmp_path, capsys, real_git):
    cfg = _cfg(tmp_path)
    task = _task_dir(tmp_path)

    # Must not raise — a non-git coga checkout is a soft no-op.
    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "not a git repo" in capsys.readouterr().err


def test_sync_nonfatal_on_rev_parse_failure(tmp_path, monkeypatch, real_git, capsys):
    cfg = _cfg(tmp_path)
    task = _task_dir(tmp_path)

    class Result:
        returncode = 128
        stdout = ""
        stderr = "fatal: detected dubious ownership in repository"

    monkeypatch.setattr(git.subprocess, "run", lambda *a, **k: Result())

    # A broken local git is surfaced loudly but does not abort the command.
    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "sync failed" in capsys.readouterr().err
    assert "sync failed" in _global_log(cfg)


def test_sync_suppressed_when_disabled(tmp_path, capsys, real_git):
    cfg = _cfg(tmp_path, git_enabled=False)
    task = _task_dir(tmp_path)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "disabled" in capsys.readouterr().err


# --- control branch mismatch (fresh-repo `master` vs `main`) -------------------


def test_sync_skips_with_guidance_when_control_branch_absent(git_repo, capsys):
    """The fresh-repo mismatch: control branch `main` doesn't exist locally
    (the repo is on `master`). Sync must not fetch/push a missing branch and
    raise a confusing swallowed GitError — it soft-skips with an actionable
    message naming the `[git].control_branch` fix, committing nothing."""
    cfg = load_config(git_repo.coga_os)
    git_repo.git("branch", "-m", "main", "master")
    git_repo.git("update-ref", "-d", "refs/remotes/origin/main")
    git_repo.git("remote", "remove", "origin")
    task = _task_dir(git_repo.coga_os)

    # Must not raise.
    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    err = capsys.readouterr().err
    assert "control branch 'main' does not exist" in err
    assert "you are on 'master'" in err
    assert 'control_branch = "master"' in err
    # Nothing landed and the task dir is left uncommitted in the working tree.
    assert not git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    assert "tasks/" in git_repo.git("status", "--porcelain")


def test_sync_allows_remote_only_control_branch(git_repo, capsys):
    """A feature checkout may have remote `main` but no local control ref.

    That is not the fresh-repo mismatch: the existing cross-branch path can
    fetch and land on the configured remote branch, so the guidance guard must
    not soft-skip it.
    """
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    git_repo.git("branch", "-D", "main")
    git_repo.git("update-ref", "-d", "refs/remotes/origin/main")
    task = _task_dir(git_repo.coga_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    err = capsys.readouterr().err
    assert "control branch 'main' does not exist" not in err
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    assert "Ticket: demo — created" in git_repo.origin_subjects()


def test_sync_skips_on_fresh_unborn_master_repo(tmp_path, capsys, real_git):
    """The literal Getting-Started case: `git init` defaulted to `master` with no
    commits yet, control branch still `main`. The unborn branch makes
    `_current_branch` (`rev-parse --abbrev-ref HEAD`) raise, so the guard must
    fire *before* it — soft-skip with guidance, never a crash."""
    subprocess.run(
        ["git", "init", "-b", "master", str(tmp_path)],
        check=True, capture_output=True, text=True,
    )
    task = _task_dir(tmp_path)
    cfg = _cfg(tmp_path)

    # Must not raise on the unborn branch.
    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    err = capsys.readouterr().err
    assert "control branch 'main' does not exist" in err
    assert "you are on 'master'" in err
    assert 'control_branch = "master"' in err


def test_sync_log_skips_with_guidance_when_control_branch_absent(git_repo, capsys):
    """`sync_log` shares the mismatch guard: a missing control branch skips the
    log commit with the same guidance, leaving the line uncommitted (not a crash)."""
    cfg = load_config(git_repo.coga_os)
    git_repo.git("branch", "-m", "main", "master")
    git_repo.git("update-ref", "-d", "refs/remotes/origin/main")
    git_repo.git("remote", "remove", "origin")
    append_log(cfg, "bootstrap/orient", "human:nick", "launched")

    git.sync_log(cfg, message="Log: bootstrap/orient")

    err = capsys.readouterr().err
    assert "control branch 'main' does not exist" in err
    assert 'control_branch = "master"' in err
    assert "log.md" in git_repo.git("status", "--porcelain")
    assert not git_repo.origin_tracks("coga/log.md")


def test_control_branch_present_detects_missing_ref(git_repo):
    """The guard keys on the control ref existing, not on what's checked out."""
    root = git_repo.root
    assert git._control_branch_present(root, "main", "origin") is True
    git_repo.checkout_branch("feature/x")
    git_repo.git("branch", "-D", "main")
    assert git._control_branch_present(root, "main", "origin") is True
    git_repo.git("update-ref", "-d", "refs/remotes/origin/main")
    assert git._control_branch_present(root, "main", "origin") is True
    assert git._control_branch_present(root, "nonexistent", "origin") is False


def test_symbolic_head_resolves_branch_and_none_when_detached(git_repo):
    """`_symbolic_head` names the branch (even pre-first-commit) for the guidance
    message, and is a quiet None on a detached HEAD."""
    root = git_repo.root
    assert git._symbolic_head(root) == "main"
    git_repo.git("checkout", "--detach", "HEAD")
    assert git._symbolic_head(root) is None


def test_sync_noop_when_nothing_changed(git_repo):
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")
    before = git_repo.origin_subjects()
    # Second call: the files are already committed and unchanged → nothing
    # staged → no second commit, no push.
    git.sync_task_state(cfg, task, message="Ticket: demo — again")

    assert git_repo.origin_subjects() == before


def test_sync_control_branch_retries_on_non_fast_forward(git_repo):
    """On `main`, a competing remote push is absorbed by fetch+rebase, not dropped.

    Regression: the same-branch path used a bare `git push` with no fetch-first
    and no retry, so any concurrent remote commit (a merged PR, another machine)
    left every later coga push on `main` rejected and silently swallowed, with
    the local branch accumulating unpushed commits.
    """
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)

    # Another process lands an unrelated file on origin/main first.
    git_repo.push_competing_commit("RIVAL.txt", "landed first\n")

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    # Both the competing file and our task file are on origin/main — anti-clobber.
    assert git_repo.origin_tracks("RIVAL.txt")
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    subjects = git_repo.origin_subjects()
    assert "Ticket: demo — created" in subjects
    assert "competing: RIVAL.txt" in subjects


def test_sync_control_branch_nonff_preserves_dirty_worktree(git_repo):
    """The fetch+rebase recovery autostashes unrelated dirty changes, not loses them."""
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)
    stray = git_repo.root / "STRAY.txt"
    stray.write_text("uncommitted user work\n")

    git_repo.push_competing_commit("RIVAL.txt", "landed first\n")
    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    # Pushed despite the moved origin...
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    assert git_repo.origin_tracks("RIVAL.txt")
    # ...and the user's uncommitted file survived the rebase, still uncommitted.
    assert stray.read_text() == "uncommitted user work\n"
    assert "STRAY.txt" in git_repo.git("status", "--porcelain")
    assert not git_repo.origin_tracks("STRAY.txt")


def test_sync_control_branch_unpoppable_dirty_change_leaves_no_markers_or_stash(
    git_repo, capsys
):
    """Hardened recovery: a dirty *tracked* change that can't replay onto the
    moved tip is rolled back cleanly — no conflict markers, no orphaned stash,
    no lingering rebase — and the miss is non-fatal.

    This is the exact autostash wound the fix targets: previously the autostash
    pop conflicted, `rebase --abort` re-conflicted, and the repo was left with
    `<<<<<<<` markers in the working tree AND an undropped stash. The explicit
    stash dance must instead restore the pre-sync state.
    """
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)

    shared = git_repo.coga_os / "workflows" / "direct" / "body.md"
    original = shared.read_text()
    # A dirty tracked edit locally...
    shared.write_text(original + "\nlocal dirty edit\n")
    # ...and a rival edit to the SAME file on origin/main → the stash pop, after
    # the task commit rebases onto the rival tip, cannot apply cleanly.
    git_repo.push_competing_commit(
        "coga/workflows/direct/body.md", original + "\nrival edit\n"
    )

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    # Non-fatal miss surfaced.
    assert "sync failed" in capsys.readouterr().err
    # No lingering rebase, no conflict markers, no orphaned stash.
    assert not (git_repo.root / ".git" / "rebase-merge").exists()
    assert not (git_repo.root / ".git" / "rebase-apply").exists()
    assert git_repo.git("stash", "list").strip() == ""
    body = shared.read_text()
    assert "<<<<<<<" not in body
    # The dirty change is preserved, restored onto the pre-sync tip.
    assert "local dirty edit" in body
    assert "rival edit" not in body


def test_sync_control_branch_retry_loop_survives_mid_flight_race(git_repo, monkeypatch):
    """Force a non-ff *between* fetch and push on `main`: the loop rebases and succeeds."""
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)

    real_push = git._push_ref
    calls = {"n": 0}

    def racing_push(root, remote, refspec):
        calls["n"] += 1
        if calls["n"] == 1:
            # A rival lands first, after we already committed — our push is non-ff.
            git_repo.push_competing_commit("RIVAL.txt", "raced in\n")
        return real_push(root, remote, refspec)

    monkeypatch.setattr(git, "_push_ref", racing_push)

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert calls["n"] >= 2  # first push rejected, rebased, retried
    assert git_repo.origin_tracks("RIVAL.txt")
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")


def test_sync_control_branch_nonfatal_on_rebase_conflict(git_repo, capsys):
    """An unresolvable rebase during recovery aborts cleanly and is non-fatal.

    The local coga commit and the competing remote commit touch the *same*
    file, so the rebase conflicts. We must abort (no lingering rebase state) and
    surface the miss to stderr + log without crashing.
    """
    cfg = load_config(git_repo.coga_os)
    task = _task_dir(git_repo.coga_os)

    # Local coga commit writes the task's ticket; the rival writes the SAME path
    # with different content on origin/main → guaranteed rebase conflict.
    git_repo.push_competing_commit(
        "coga/tasks/demo/ticket.md", "rival content\n"
    )

    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    err = capsys.readouterr().err
    assert "sync failed" in err
    assert "sync failed" in _global_log(cfg)
    # The repo is not left mid-rebase.
    assert not (git_repo.root / ".git" / "rebase-merge").exists()
    assert not (git_repo.root / ".git" / "rebase-apply").exists()


def test_sync_nonfatal_on_push_failure(git_repo, capsys):
    """A failed push is surfaced (stderr + log) but never crashes the command."""
    cfg = load_config(git_repo.coga_os)
    git_repo.git("remote", "remove", "origin")
    task = _task_dir(git_repo.coga_os)

    # Must not raise.
    git.sync_task_state(cfg, task, message="Ticket: demo — created")

    assert "sync failed" in capsys.readouterr().err
    assert "sync failed" in _global_log(cfg)


# --- CLI integration through real git ------------------------------------------


def test_cli_create_then_activate_sync_to_origin(git_repo):
    result = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    assert result.exit_code == 0, result.output
    slug = result.output.split(":", 1)[0].strip()

    activated = runner.invoke(app, ["mark", "active", slug])
    assert activated.exit_code == 0, activated.output

    subjects = git_repo.origin_subjects()
    assert f"Ticket: {slug} — created" in subjects
    assert f"Ticket: {slug} — active" in subjects
    assert git_repo.origin_tracks(f"coga/tasks/{slug}.md")


def test_cli_bump_syncs_step_to_origin(git_repo):
    result = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = result.output.split(":", 1)[0].strip()
    runner.invoke(app, ["mark", "active", slug])

    # Move to in_progress by hand (launch normally does this, but it spawns an
    # agent). The hand edit is swept into the bump's commit — fine for the test.
    ticket = git_repo.coga_os / "tasks" / f"{slug}.md"
    ticket.write_text(ticket.read_text().replace("status: active", "status: in_progress"))

    bumped = runner.invoke(app, ["bump", slug])
    assert bumped.exit_code == 0, bumped.output

    assert any(
        s.startswith(f"Ticket: {slug} — step 2 (review)")
        for s in git_repo.origin_subjects()
    )


# --- bespoke call sites (ticket C): panic + ticket authoring -------------------
#
# A wired the clean finalizers (mark/bump/create/retire). C wires the two sites
# that don't go through those: `coga panic` (blocker written straight to the
# blackboard + log) and `coga ticket` authoring (the agent edits ticket.md in
# a subprocess, so coga must commit the result after control returns).


def test_cli_panic_syncs_blocker_to_origin(git_repo):
    """`coga panic` lands the blocker (blackboard + log) on origin/main."""
    result = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = result.output.split(":", 1)[0].strip()

    panicked = runner.invoke(
        app, ["panic", "--task", slug, "--reason", "retry ceiling unspecified"]
    )
    # Panic exits non-zero by design (the distress signal), but the sync still
    # ran before the exit.
    assert panicked.exit_code == 1, panicked.output

    assert any(
        s.startswith(f"Ticket: {slug} — panic") for s in git_repo.origin_subjects()
    )
    # The blocker is appended to the blackboard region of the single-file
    # ticket (the file-form `tasks/<slug>.md`; no separate blackboard.md).
    ticket = git_repo.git(
        "show", f"main:coga/tasks/{slug}.md", cwd=git_repo.origin
    )
    assert "retry ceiling unspecified" in ticket


def test_cli_panic_from_feature_branch_leaves_code_untouched(git_repo):
    """Panic often fires from a feature worktree with uncommitted code.

    The blocker must land on origin/main, but uncommitted *code* in the
    worktree must NOT be swept into the commit (the whole reason C scopes
    strictly to the task dir).
    """
    result = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = result.output.split(":", 1)[0].strip()
    git_repo.checkout_branch("feature/x")

    stray = git_repo.root / "wip.py"
    stray.write_text("# half-written change\n")

    panicked = runner.invoke(
        app, ["panic", "--task", slug, "--reason", "blocked on design"]
    )
    assert panicked.exit_code == 1, panicked.output

    # Blocker landed on the control branch...
    assert any(
        s.startswith(f"Ticket: {slug} — panic") for s in git_repo.origin_subjects()
    )
    # ...but the uncommitted code did not, and is still sitting in the worktree.
    assert not git_repo.origin_tracks("wip.py")
    assert "wip.py" in git_repo.git("status", "--porcelain")


def _seed_ticket_bootstrap(coga_os: Path) -> None:
    """Add the `bootstrap/ticket` launch target + skill the `coga ticket` cmd launches."""
    bootstrap_dir = coga_os / "bootstrap" / "ticket"
    bootstrap_dir.mkdir(parents=True)
    (bootstrap_dir / "ticket.md").write_text(
        dedent(
            """
            ---
            title: Create a new ticket
            mode: interactive
            skills:
              - bootstrap/ticket
            assignee: claude
            ---

            ## Description

            Persistent launch target.
            """
        ).lstrip()
    )
    skill = coga_os / "skills" / "bootstrap" / "ticket"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        dedent(
            """
            ---
            name: bootstrap/ticket
            description: Author a Coga task.
            ---

            Interview and fill the ticket.
            """
        ).lstrip()
    )


def _fake_authoring_agent(monkeypatch, *, on_run=None) -> None:
    """Stub the spawned authoring agent: fake a TTY, resolve the CLI, and run
    `on_run` (which stands in for the agent's external edits) instead of a real
    subprocess.

    Patching `launch.subprocess.run` patches the module-global `run`, which the
    real git sync (also a `subprocess.run` caller) would otherwise hit — so git
    invocations are delegated to the real `run`; only the agent launch is faked.
    """
    import subprocess as _subprocess

    real_run = _subprocess.run

    class _Result:
        returncode = 0

    def fake_run(cmd, *args, **kwargs):
        if cmd and cmd[0] == "git":
            return real_run(cmd, *args, **kwargs)
        if on_run is not None:
            on_run()
        return _Result()

    monkeypatch.setattr(
        "coga.commands.ticket._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga.commands.ticket.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run)


def test_cli_ticket_authoring_syncs_edits_to_origin(git_repo, monkeypatch):
    """The agent's external edits to ticket.md are committed + pushed by coga."""
    _seed_ticket_bootstrap(git_repo.coga_os)
    result = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = result.output.split(":", 1)[0].strip()
    ticket_path = git_repo.coga_os / "tasks" / f"{slug}.md"

    def author():
        t = Ticket.read(ticket_path)
        t.body = t.body + "\n\nAuthored during the session.\n"
        t.write(ticket_path)

    _fake_authoring_agent(monkeypatch, on_run=author)

    authored = runner.invoke(app, ["ticket", slug])
    assert authored.exit_code == 0, authored.output

    assert any(
        s.startswith(f"Ticket: {slug} — authored")
        for s in git_repo.origin_subjects()
    )
    body = git_repo.git(
        "show", f"main:coga/tasks/{slug}.md", cwd=git_repo.origin
    )
    assert "Authored during the session." in body


def test_cli_ticket_authoring_syncs_a_newly_created_task(git_repo, monkeypatch):
    """`coga ticket "<title>"` with no existing task syncs the draft it creates.

    The authoring flow creates a brand-new task mid-session, so there is no
    pre-resolved `TaskRef` to sync. `sync_paths` picks it up via the
    before/after snapshot of `tasks/`, then commits + pushes it as authored.
    """
    _seed_ticket_bootstrap(git_repo.coga_os)

    def author():
        path = git_repo.coga_os / "tasks" / "fresh-idea.md"
        t = Ticket.read(path)
        t.frontmatter["workflow"] = "code"  # a draft must land on a workflow
        t.body = t.body + "\n\nFleshed out during authoring.\n"
        t.write(path)

    _fake_authoring_agent(monkeypatch, on_run=author)

    result = runner.invoke(app, ["ticket", "Fresh idea"])
    assert result.exit_code == 0, result.output

    assert git_repo.origin_tracks("coga/tasks/fresh-idea.md")
    assert any(
        s.startswith("Ticket: fresh-idea — authored")
        for s in git_repo.origin_subjects()
    )
    body = git_repo.git(
        "show", "main:coga/tasks/fresh-idea.md", cwd=git_repo.origin
    )
    assert "Fleshed out during authoring." in body


def test_cli_ticket_authoring_records_session_without_ticket_edits(git_repo, monkeypatch):
    """Even when the agent edits no ticket fields, the session is still synced.

    `coga ticket` appends a "ticket authoring launched" line to `log.md`
    *before* spawning the agent, so the task dir always has something to sync —
    the authoring attempt lands on origin even if the ticket body is untouched.
    (The genuine nothing-staged no-op is covered at the helper level by
    `test_sync_noop_when_nothing_changed`.)
    """
    _seed_ticket_bootstrap(git_repo.coga_os)
    result = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = result.output.split(":", 1)[0].strip()

    _fake_authoring_agent(monkeypatch, on_run=None)  # agent edits nothing

    authored = runner.invoke(app, ["ticket", slug])
    assert authored.exit_code == 0, authored.output

    assert any(
        s.startswith(f"Ticket: {slug} — authored")
        for s in git_repo.origin_subjects()
    )
    # The authoring line lands in the repo-global `coga/log.md` now, which
    # rides the same-branch commit+push on `main` to origin.
    log = git_repo.git(
        "show", "main:coga/log.md", cwd=git_repo.origin
    )
    assert "ticket authoring launched" in log


# --- delete (the sync gap this fixes) -----------------------------------------
#
# `coga delete` removes the task dir through the `bootstrap/delete-task` skill
# but historically never synced — the lone state mutation that left an
# uncommitted working-tree deletion. It now lands the removal on the control
# branch like every other command.

_DELETE_SKILL_SRC = (
    Path(__file__).resolve().parents[1]
    / "src" / "coga" / "resources" / "templates" / "coga"
    / "bootstrap" / "skills" / "bootstrap" / "delete-task"
)


def _install_delete_skill(coga_os: Path) -> None:
    import shutil

    shutil.copytree(
        _DELETE_SKILL_SRC, coga_os / "skills" / "bootstrap" / "delete-task"
    )


def test_cli_delete_syncs_removal_to_origin(git_repo):
    """`coga delete` lands the directory removal on origin/main.

    The created ticket is committed first; deleting it must produce a real
    deletion commit, not an orphaned working-tree change.
    """
    _install_delete_skill(git_repo.coga_os)
    created = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = created.output.split(":", 1)[0].strip()
    assert git_repo.origin_tracks(f"coga/tasks/{slug}.md")

    deleted = runner.invoke(app, ["delete", slug])
    assert deleted.exit_code == 0, deleted.output

    # The removal landed: a deletion commit on origin, and the path is gone from
    # the control-branch tree — not merely from the local working copy.
    assert f"Ticket: {slug} — deleted" in git_repo.origin_subjects()
    assert not git_repo.origin_tracks(f"coga/tasks/{slug}.md")
    # And nothing is left dirty in the working tree (the bug's symptom).
    status = git_repo.git("status", "--porcelain", cwd=git_repo.root)
    assert slug not in status


# --- non-interactive git (no credential-prompt hangs) -------------------------
#
# Regression: coga's git sync runs unattended inside `coga launch` / `bump` /
# `mark`. With an HTTPS remote and `gh` logged out (gh is the credential
# helper), a push had no creds and git dropped into an interactive credential
# prompt that hung the launch instead of failing loud. Every git invocation
# must run with the terminal prompt disabled so that surfaces as a GitError.


class _OkResult:
    returncode = 0
    stdout = ""
    stderr = ""


def _capture_run(monkeypatch):
    """Patch `git.subprocess.run`, returning a list that collects each env."""
    envs: list[dict | None] = []

    def fake_run(cmd, *args, **kwargs):
        envs.append(kwargs.get("env"))
        return _OkResult()

    monkeypatch.setattr(git.subprocess, "run", fake_run)
    return envs


def test_noninteractive_env_disables_terminal_prompt(monkeypatch):
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)
    env = git._noninteractive_git_env()
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert "BatchMode=yes" in env["GIT_SSH_COMMAND"]


def test_noninteractive_env_preserves_operator_ssh_command(monkeypatch):
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh -i /my/key")
    env = git._noninteractive_git_env()
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    # The operator's own SSH command is left untouched, not clobbered.
    assert "GIT_SSH_COMMAND" not in env


def test_run_git_runs_non_interactively(monkeypatch, tmp_path):
    envs = _capture_run(monkeypatch)
    git._run_git(tmp_path, "status")
    assert envs[0] is not None
    assert envs[0]["GIT_TERMINAL_PROMPT"] == "0"


def test_run_git_overlay_preserves_caller_env(monkeypatch, tmp_path):
    envs = _capture_run(monkeypatch)
    git._run_git(tmp_path, "write-tree", env={"GIT_INDEX_FILE": "/tmp/idx"})
    assert envs[0]["GIT_TERMINAL_PROMPT"] == "0"
    assert envs[0]["GIT_INDEX_FILE"] == "/tmp/idx"


def test_push_ref_runs_non_interactively(monkeypatch, tmp_path):
    envs = _capture_run(monkeypatch)
    assert git._push_ref(tmp_path, "origin", "main") is None
    assert envs[0]["GIT_TERMINAL_PROMPT"] == "0"


# --- sync_coga_state: the catch-all subtree sweep ------------------------------


def test_sync_coga_state_commits_dirty_coga_and_leaves_code_untouched(git_repo):
    """The sweep commits dirty `coga/` OS state (incl. an untracked new ticket,
    the usage-record-style side-effect) and pushes it, while a modified tracked
    file *outside* `coga/` (product code) is never swept in."""
    cfg = load_config(git_repo.coga_os)
    # A tracked file outside the coga/ subtree, then dirtied — stands in for the
    # `src/` product code the "Scope is narrow" rule protects.
    outside = git_repo.root / "outside.txt"
    outside.write_text("original\n")
    git_repo.git("add", "outside.txt")
    git_repo.git("commit", "-m", "seed outside")
    git_repo.git("push", "origin", "main")
    outside.write_text("locally modified\n")

    # Dirty state under coga/: an untracked new ticket (a machine write past the
    # last per-command sync).
    _task_dir(git_repo.coga_os)

    git.sync_coga_state(cfg, message="Sync coga state")

    # coga/ is committed (clean tree) and pushed; the untracked ticket rode along.
    assert "coga/" not in git_repo.git("status", "--porcelain")
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    assert "Sync coga state" in git_repo.origin_subjects()
    # The code file outside coga/ is left dirty and unpushed.
    assert "outside.txt" in git_repo.git("status", "--porcelain")
    assert git_repo.git("show", "origin/main:outside.txt") == "original\n"


def test_sync_coga_state_lands_nonunion_on_main_keeps_union_local_on_feature(git_repo):
    """From a feature branch: non-union coga/ state lands on origin/main via the
    overlay, but a `merge=union` file (log.md) is committed locally only — never
    landed via the wholesale-replace overlay that would drop concurrent lines."""
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    _task_dir(git_repo.coga_os)
    append_log(cfg, "demo", "human:nick", "hand note")

    git.sync_coga_state(cfg, message="Sync coga state")

    # The whole subtree is committed locally — clean feature tree.
    assert "coga/" not in git_repo.git("status", "--porcelain")
    # Non-union ticket landed on the shared control branch...
    assert git_repo.origin_tracks("coga/tasks/demo/ticket.md")
    # ...but the union log.md did NOT ride the overlay onto origin/main...
    assert not git_repo.origin_tracks("coga/log.md")
    # ...while it IS committed on the feature branch (reaches main via PR merge).
    assert "hand note" in git_repo.git("show", "HEAD:coga/log.md")


def test_sync_coga_state_noop_on_clean_subtree(git_repo):
    """A clean coga/ subtree is a silent no-op: no commit, nothing pushed."""
    cfg = load_config(git_repo.coga_os)
    before = git_repo.origin_subjects()

    git.sync_coga_state(cfg, message="Sync coga state")

    assert git_repo.origin_subjects() == before


def test_sync_coga_state_suppressed_when_disabled(tmp_path, capsys, real_git):
    cfg = load_config(_write_config(tmp_path, local_extra="[git]\nenabled = false\n"))
    git.sync_coga_state(cfg, message="Sync coga state")
    assert "disabled (sync suppressed)" in capsys.readouterr().err


def test_sweep_skips_read_only_and_runs_for_mutating_commands(monkeypatch):
    """The CLI-dispatch boundary sweeps mutating commands only — never read-only
    renders (principles #6), `--help`, or a repo-less invocation."""
    from coga import cli

    calls: list[object] = []
    monkeypatch.setattr(cli.git, "sync_coga_state", lambda cfg, **k: calls.append(cfg))
    cfg = object()

    monkeypatch.setattr(cli.sys, "argv", ["coga", "status"])
    cli._sweep_coga_state(cfg)
    assert calls == []  # read-only command

    monkeypatch.setattr(cli.sys, "argv", ["coga", "bump", "demo"])
    cli._sweep_coga_state(cfg)
    assert calls == [cfg]  # mutating command swept

    calls.clear()
    cli._sweep_coga_state(None)
    assert calls == []  # no repo → nothing to sweep

    monkeypatch.setattr(cli.sys, "argv", ["coga", "bump", "--help"])
    cli._sweep_coga_state(cfg)
    assert calls == []  # help is not a state change
