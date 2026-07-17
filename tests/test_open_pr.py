"""Tests for `coga.open_pr`, the deterministic push→PR→record recipe behind
the `coga open-pr` command.

Uses the real-git harness (`init_git_repo`) so branch/commit/push behaviour is
exercised for real against a bare `origin`, and a fake `gh` on PATH so the PR
calls are observable without a network. The two headline paths mirror the
ticket's acceptance: fail loud (and do NOT produce a PR) when there is nothing
committed to open, and open + record a real PR when there is.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from textwrap import dedent

import pytest

from conftest import init_git_repo
from coga.autoclose import parse_pr_url, parse_worktree_path
from coga.config import load_config
from coga.github_preflight import CheckResult
from coga.open_pr import OpenPrError, open_pr, set_dev_pr
from coga.taskfile import read_blackboard


# --- fixtures / helpers -------------------------------------------------------


def _install_fake_gh(
    monkeypatch: pytest.MonkeyPatch,
    bin_dir: Path,
    *,
    create_url: str = "https://github.com/acme/repo/pull/7",
    view_json: dict | None = None,
) -> Path:
    """Put a fake `gh` on PATH and return the file it logs invocations to.

    `pr view` exits 1 (no PR) unless `view_json` is given, in which case it
    prints that JSON and exits 0; `pr create` prints `create_url`; `pr ready`
    exits 0. Every call is appended to the returned log file.
    """
    log = bin_dir / "gh-calls.log"
    view_file = bin_dir / "view.json"
    if view_json is not None:
        view_file.write_text(json.dumps(view_json))
    gh = bin_dir / "gh"
    gh.write_text(
        dedent(
            f"""
            #!/usr/bin/env bash
            echo "$@" >> {str(log)!r}
            case "$1 $2" in
              "pr view")
                if [ -f {str(view_file)!r} ]; then cat {str(view_file)!r}; exit 0; fi
                exit 1 ;;
              "pr create") echo {create_url!r}; exit 0 ;;
              "pr ready") exit 0 ;;
              *) exit 0 ;;
            esac
            """
        ).lstrip()
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return log


def _feature_worktree(repo, tmp_path: Path, branch: str, *, commit: bool) -> Path:
    """Create a feature worktree off `main`, optionally with a commit ahead."""
    wt = tmp_path / f"wt-{branch}"
    repo.git("worktree", "add", str(wt), "-b", branch, "main")
    if commit:
        (wt / "coga" / "change.txt").write_text("a real change\n")
        repo.git("add", "-A", cwd=wt)
        repo.git("commit", "-m", "feature: a real change", cwd=wt)
    return wt


def _write_ticket(
    coga_os: Path,
    slug: str,
    *,
    branch: str,
    worktree: Path | None,
    description: str = "The change we are shipping.",
    pr_section: str | None = None,
    pr: str = "",
) -> Path:
    task_dir = coga_os / "tasks" / slug
    task_dir.mkdir(parents=True, exist_ok=True)
    dev_lines = [f"branch: {branch}"]
    if worktree is not None:
        dev_lines.append(f"worktree: {worktree}")
    if pr:
        dev_lines.append(f"pr: {pr}")
    pr_block = f"\n## PR\n\n{pr_section}\n" if pr_section else ""
    # Built at column 0 (no dedent): the injected `## Dev` lines are unindented,
    # so dedent would find no common leading whitespace and strip nothing.
    frontmatter = (
        "---\n"
        f"slug: {slug}\n"
        "title: Ship the change\n"
        "status: in_progress\n"
        "owner: marc\n"
        "human: marc\n"
        "agent: claude\n"
        "assignee: claude\n"
        "contexts: []\n"
        "skills: []\n"
        "workflow:\n"
        "  name: code/with-review\n"
        "  steps:\n"
        "    - name: open-pr\n"
        "    - name: review\n"
        "step: 1 (open-pr)\n"
        "secrets: null\n"
        "script: null\n"
        "---\n"
    )
    body = (
        f"\n## Description\n\n{description}\n\n"
        "<!-- coga:blackboard -->\n\n"
        "## Dev\n"
        f"{chr(10).join(dev_lines)}\n"
        f"{pr_block}"
    )
    ticket = task_dir / "ticket.md"
    ticket.write_text(frontmatter + body)
    return ticket


# --- happy path ---------------------------------------------------------------


def test_open_pr_opens_and_records_url(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/7")

    wt = _feature_worktree(repo, tmp_path, "feature-x", commit=True)
    ticket = _write_ticket(repo.coga_os, "ship-it", branch="feature-x", worktree=wt)

    cfg = load_config(repo.coga_os)
    url = open_pr(cfg, slug="ship-it", blackboard_path=ticket)

    assert url == "https://github.com/acme/repo/pull/7"
    # The branch actually landed on origin, and gh create was invoked.
    assert repo.git("rev-parse", "--verify", "refs/heads/feature-x", cwd=repo.origin).strip()
    calls = log.read_text()
    assert "pr create" in calls
    # pr: recorded back under ## Dev.
    assert parse_pr_url(read_blackboard(ticket)) == url


def test_open_pr_body_falls_back_to_description(tmp_path, monkeypatch):
    """No `## PR` section → the PR body is the ticket's `## Description`."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    wt = _feature_worktree(repo, tmp_path, "feature-y", commit=True)
    ticket = _write_ticket(
        repo.coga_os, "desc-body", branch="feature-y", worktree=wt,
        description="DISTINCTIVE-DESCRIPTION-BODY",
    )
    cfg = load_config(repo.coga_os)
    open_pr(cfg, slug="desc-body", blackboard_path=ticket)

    # gh create was called with a --body arg carrying the description + Closes line.
    calls = log.read_text()
    assert "DISTINCTIVE-DESCRIPTION-BODY" in calls
    assert "Closes ticket: `desc-body`" in calls


def test_open_pr_readies_existing_draft(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(
        monkeypatch, bin_dir,
        view_json={
            "url": "https://github.com/acme/repo/pull/3",
            "state": "OPEN",
            "isDraft": True,
            "number": 3,
        },
    )
    wt = _feature_worktree(repo, tmp_path, "feature-draft", commit=True)
    ticket = _write_ticket(repo.coga_os, "ready-draft", branch="feature-draft", worktree=wt)

    cfg = load_config(repo.coga_os)
    url = open_pr(cfg, slug="ready-draft", blackboard_path=ticket)

    assert url == "https://github.com/acme/repo/pull/3"
    calls = log.read_text()
    assert "pr ready https://github.com/acme/repo/pull/3" in calls
    assert "pr create" not in calls  # reused the draft, did not open a new PR
    assert parse_pr_url(read_blackboard(ticket)) == url


# --- fail-loud paths (the whole point) ---------------------------------------


def test_open_pr_fails_when_no_commits_ahead(tmp_path, monkeypatch):
    """The incident case: a branch with nothing built must fail loud, not PR."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    wt = _feature_worktree(repo, tmp_path, "empty-branch", commit=False)
    ticket = _write_ticket(repo.coga_os, "nothing-built", branch="empty-branch", worktree=wt)

    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="no commits ahead"):
        open_pr(cfg, slug="nothing-built", blackboard_path=ticket)

    # No PR opened, nothing pushed, no pr: recorded.
    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def test_open_pr_fails_when_branch_missing(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    ticket = _write_ticket(
        repo.coga_os, "no-branch", branch="(not yet created)", worktree=None,
    )
    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="branch:"):
        open_pr(cfg, slug="no-branch", blackboard_path=ticket)


def test_open_pr_fails_when_worktree_missing(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    # A branch recorded but no worktree line at all.
    ticket = _write_ticket(repo.coga_os, "no-wt", branch="feature-z", worktree=None)
    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="worktree:"):
        open_pr(cfg, slug="no-wt", blackboard_path=ticket)


def test_open_pr_fails_when_worktree_dirty(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "dirty-branch", commit=True)
    (wt / "coga" / "uncommitted.txt").write_text("dirty\n")
    ticket = _write_ticket(repo.coga_os, "dirty", branch="dirty-branch", worktree=wt)

    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="uncommitted changes"):
        open_pr(cfg, slug="dirty", blackboard_path=ticket)


def test_open_pr_fails_with_setup_hint_before_push_when_gh_missing(
    tmp_path, monkeypatch
):
    repo = init_git_repo(tmp_path)
    wt = _feature_worktree(repo, tmp_path, "missing-gh", commit=True)
    ticket = _write_ticket(
        repo.coga_os, "missing-gh", branch="missing-gh", worktree=wt
    )
    monkeypatch.setattr(
        "coga.open_pr.check_gh_auth",
        lambda _host: CheckResult(
            "gh-auth",
            False,
            "`gh` is not installed — install it from https://cli.github.com "
            "and run `gh auth login`.",
        ),
    )

    with pytest.raises(OpenPrError, match="cli.github.com"):
        open_pr(load_config(repo.coga_os), slug="missing-gh", blackboard_path=ticket)

    # Point-of-need failure happens before the feature branch is pushed.
    remote_branches = repo.git(
        "for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=repo.origin
    ).splitlines()
    assert "missing-gh" not in remote_branches


def test_open_pr_fails_when_branch_has_material_stale_drift(tmp_path, monkeypatch):
    """A branch missing a material control change must fail loud, not open a PR.

    This is the #518 stale-branch guard the old agent checklist ran via
    `coga validate --check-github`; the deterministic command carries it
    forward. Branch off main, then advance `origin/main` from a competing clone.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    wt = _feature_worktree(repo, tmp_path, "stale-branch", commit=True)
    # Another process lands on origin/main after we branched → we are behind it.
    repo.push_competing_commit("coga/rival.txt", "landed elsewhere\n")
    ticket = _write_ticket(repo.coga_os, "stale", branch="stale-branch", worktree=wt)

    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="not safe to publish"):
        open_pr(cfg, slug="stale", blackboard_path=ticket)

    # No PR opened, no pr: recorded.
    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def test_open_pr_retry_after_rebase_uses_force_with_lease(tmp_path, monkeypatch):
    """A pushed branch can be rebased and safely republished on retry."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)

    wt = _feature_worktree(repo, tmp_path, "rebased-retry", commit=True)
    ticket = _write_ticket(
        repo.coga_os, "retry", branch="rebased-retry", worktree=wt
    )
    cfg = load_config(repo.coga_os)
    open_pr(cfg, slug="retry", blackboard_path=ticket)
    old_remote = repo.git(
        "rev-parse", "refs/heads/rebased-retry", cwd=repo.origin
    ).strip()

    repo.push_competing_commit("src/base-change.txt", "new base\n")
    repo.git("fetch", "origin", "main", cwd=wt)
    repo.git("rebase", "FETCH_HEAD", cwd=wt)
    new_head = repo.git("rev-parse", "HEAD", cwd=wt).strip()
    assert new_head != old_remote

    open_pr(cfg, slug="retry", blackboard_path=ticket)

    assert (
        repo.git("rev-parse", "refs/heads/rebased-retry", cwd=repo.origin).strip()
        == new_head
    )


def test_open_pr_accepts_non_overlapping_coga_state_drift(
    tmp_path, monkeypatch, capsys
):
    """A step/log sync after peer review must not force a manual rebase."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    wt = _feature_worktree(repo, tmp_path, "state-drift", commit=True)
    repo.push_competing_commit("coga/tasks/other.md", "new task state\n")
    repo.push_competing_commit("coga/log.md", "new audit state\n")
    ticket = _write_ticket(
        repo.coga_os, "state-only", branch="state-drift", worktree=wt
    )

    cfg = load_config(repo.coga_os)
    url = open_pr(cfg, slug="state-only", blackboard_path=ticket)

    assert url == "https://github.com/acme/repo/pull/7"
    assert (
        "advanced only through non-overlapping Coga task/log state"
        in capsys.readouterr().out
    )
    assert "pr create" in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) == url


def test_open_pr_rejects_overlapping_coga_state_drift(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    wt = _feature_worktree(repo, tmp_path, "overlapping-state", commit=True)
    shared = wt / "coga" / "tasks" / "shared.md"
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_text("feature state\n")
    repo.git("add", "--", "coga/tasks/shared.md", cwd=wt)
    repo.git("commit", "-m", "feature: touch shared state", cwd=wt)
    repo.push_competing_commit("coga/tasks/shared.md", "control state\n")
    ticket = _write_ticket(
        repo.coga_os, "overlap", branch="overlapping-state", worktree=wt
    )

    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="Overlapping paths: coga/tasks/shared.md"):
        open_pr(cfg, slug="overlap", blackboard_path=ticket)

    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def test_open_pr_rejects_task_rename_overlapping_feature_edit(
    tmp_path, monkeypatch
):
    """A control rename must retain its old path for overlap detection."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    original = repo.coga_os / "tasks" / "original.md"
    original.write_text("base state\n")
    repo.git("add", "--", "coga/tasks/original.md")
    repo.git("commit", "-m", "seed task state")
    repo.git("push", "origin", "main")

    wt = _feature_worktree(repo, tmp_path, "rename-overlap", commit=True)
    feature_original = wt / "coga" / "tasks" / "original.md"
    feature_original.write_text("feature state\n")
    repo.git("add", "--", "coga/tasks/original.md", cwd=wt)
    repo.git("commit", "-m", "feature: edit original task", cwd=wt)

    clone = repo.origin.parent / "rename-clone"
    repo.git("clone", str(repo.origin), str(clone), cwd=repo.origin.parent)
    repo.git("config", "user.email", "rival@example.com", cwd=clone)
    repo.git("config", "user.name", "Rival", cwd=clone)
    repo.git("checkout", "-B", "main", "origin/main", cwd=clone)
    repo.git(
        "mv",
        "coga/tasks/original.md",
        "coga/tasks/renamed.md",
        cwd=clone,
    )
    repo.git("commit", "-m", "rename task state", cwd=clone)
    repo.git("push", "origin", "main", cwd=clone)

    ticket = _write_ticket(
        repo.coga_os,
        "rename-overlap",
        branch="rename-overlap",
        worktree=wt,
    )
    with pytest.raises(OpenPrError, match="coga/tasks/original.md"):
        open_pr(
            load_config(repo.coga_os),
            slug="rename-overlap",
            blackboard_path=ticket,
        )

    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


# --- set_dev_pr unit ----------------------------------------------------------


def test_set_dev_pr_updates_in_place():
    bb = "## Dev\nbranch: b\nworktree: /w\npr:\n"
    out = set_dev_pr(bb, "https://x/pull/1")
    assert "pr: https://x/pull/1" in out
    assert out.count("pr:") == 1  # overwritten, not appended


def test_set_dev_pr_inserts_when_absent():
    bb = "## Dev\nbranch: b\nworktree: /w\n"
    out = set_dev_pr(bb, "https://x/pull/2")
    assert "pr: https://x/pull/2" in out
    assert parse_worktree_path(out) == "/w"  # section still intact


def test_set_dev_pr_preserves_bullet_prefix():
    bb = "## Dev\n- branch: b\n- pr:\n"
    out = set_dev_pr(bb, "https://x/pull/3")
    assert "- pr: https://x/pull/3" in out


def test_set_dev_pr_appends_section_when_missing():
    out = set_dev_pr("some notes\n", "https://x/pull/4")
    assert "## Dev" in out
    assert "pr: https://x/pull/4" in out


# --- live/packaged skill copies stay in sync (CLAUDE.md rule) -----------------

_ROOT = Path(__file__).resolve().parents[1]
_LIVE_SKILL = _ROOT / "coga" / "skills" / "code" / "open-pr"
_PACKAGED_SKILL = (
    _ROOT / "src" / "coga" / "resources" / "templates" / "coga"
    / "bootstrap" / "skills" / "code" / "open-pr"
)


def test_open_pr_live_and_packaged_copies_stay_in_sync() -> None:
    assert (_LIVE_SKILL / "SKILL.md").read_text() == (
        _PACKAGED_SKILL / "SKILL.md"
    ).read_text()


def test_open_pr_skill_is_agent_step_not_script() -> None:
    from coga.skill import Skill

    skill = Skill.load(_LIVE_SKILL / "SKILL.md")
    assert skill.script is None
    assert not (_LIVE_SKILL / "run.py").exists()
    assert not (_LIVE_SKILL / "recipe.py").exists()
    assert not (_PACKAGED_SKILL / "run.py").exists()
    assert not (_PACKAGED_SKILL / "recipe.py").exists()
