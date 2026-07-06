"""Tests for the `coga open-pr` command — the CLI wiring over the `coga.open_pr`
recipe that the `code/open-pr` agent step runs.

The recipe itself is covered by `test_open_pr.py`; here we exercise the command
seam: it resolves the task, runs the recipe, prints the URL, and maps an
`OpenPrError` to a non-zero exit. The headline case is the one the ticket calls
out explicitly — pushing the recorded `## Dev` branch **by name** is agnostic to
which feature worktree holds it. The command itself stays on the primary
control checkout so task resolution and the blackboard write are authoritative.

Mirrors `test_open_pr.py`'s real-git harness (a bare `origin` + a fake `gh` on
PATH) so push/PR behaviour is exercised for real without a network.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from conftest import init_git_repo
from coga.autoclose import parse_pr_url
from coga.cli import app
from coga.taskfile import read_blackboard


# --- fixtures / helpers (mirrors test_open_pr.py) -----------------------------


def _install_fake_gh(
    monkeypatch: pytest.MonkeyPatch,
    bin_dir: Path,
    *,
    create_url: str = "https://github.com/acme/repo/pull/7",
) -> Path:
    """Put a fake `gh` on PATH; `pr view` says no PR, `pr create` prints the URL."""
    log = bin_dir / "gh-calls.log"
    gh = bin_dir / "gh"
    gh.write_text(
        dedent(
            f"""
            #!/usr/bin/env bash
            echo "$@" >> {str(log)!r}
            case "$1 $2" in
              "pr view") exit 1 ;;
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
    wt = tmp_path / f"wt-{branch}"
    repo.git("worktree", "add", str(wt), "-b", branch, "main")
    if commit:
        (wt / "coga" / "change.txt").write_text("a real change\n")
        repo.git("add", "-A", cwd=wt)
        repo.git("commit", "-m", "feature: a real change", cwd=wt)
    return wt


def _write_ticket(coga_os: Path, slug: str, *, branch: str, worktree: Path | None) -> Path:
    task_dir = coga_os / "tasks" / slug
    task_dir.mkdir(parents=True, exist_ok=True)
    dev_lines = [f"branch: {branch}"]
    if worktree is not None:
        dev_lines.append(f"worktree: {worktree}")
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
        "\n## Description\n\nThe change we are shipping.\n\n"
        "<!-- coga:blackboard -->\n\n"
        "## Dev\n"
        f"{chr(10).join(dev_lines)}\n"
    )
    ticket = task_dir / "ticket.md"
    ticket.write_text(frontmatter + body)
    return ticket


# --- tests --------------------------------------------------------------------


def test_open_pr_command_opens_and_records(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/7")

    wt = _feature_worktree(repo, tmp_path, "feature-x", commit=True)
    ticket = _write_ticket(repo.coga_os, "ship-it", branch="feature-x", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["open-pr", "ship-it"])

    assert result.exit_code == 0, result.output
    assert "https://github.com/acme/repo/pull/7" in result.output
    assert "pr create" in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) == "https://github.com/acme/repo/pull/7"


def test_open_pr_command_fails_loud_on_no_commits(tmp_path, monkeypatch):
    """The incident case surfaced through the CLI: nothing built → non-zero exit,
    no PR, no recorded `pr:`."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    wt = _feature_worktree(repo, tmp_path, "empty-branch", commit=False)
    ticket = _write_ticket(repo.coga_os, "nothing-built", branch="empty-branch", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["open-pr", "nothing-built"])

    assert result.exit_code == 2, result.output
    assert "no commits ahead" in result.output
    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def test_open_pr_command_unknown_task_fails_loud(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["open-pr", "no-such-task"])
    assert result.exit_code == 2, result.output


def test_open_pr_command_refuses_feature_checkout(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    wt = _feature_worktree(repo, tmp_path, "feature-x", commit=True)
    _write_ticket(repo.coga_os, "ship-it", branch="feature-x", worktree=wt)
    (wt / "coga" / "coga.local.toml").write_text('user = "marc"\n')

    monkeypatch.chdir(wt / "coga")
    result = CliRunner().invoke(app, ["open-pr", "ship-it"])

    assert result.exit_code == 2, result.output
    assert "must run from the primary control checkout" in result.output
    assert "feature-x" in result.output


def test_open_pr_command_pushes_recorded_branch_by_name(tmp_path, monkeypatch):
    """The seam the divergence incident lived in: `coga open-pr` pushes the
    branch recorded under `## Dev` **by name** while the command remains in the
    control checkout — it never pushes "current HEAD".

    Here the command runs from the control checkout (`coga_os`, sitting on
    `main`), while the feature branch lives in a *separate* worktree — exactly
    the launch-worktree-isolation layout. The recorded branch must still land on
    `origin`, proving it targets the recorded feature worktree rather than the
    command's checkout.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/9")

    wt = _feature_worktree(repo, tmp_path, "detached-feature", commit=True)
    ticket = _write_ticket(
        repo.coga_os, "by-name", branch="detached-feature", worktree=wt
    )

    # The control checkout the command runs from is on `main`, NOT the feature
    # branch — so a "push current HEAD" implementation would push the wrong ref.
    assert repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
    assert not _origin_has_branch(repo, "detached-feature")

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["open-pr", "by-name"])

    assert result.exit_code == 0, result.output
    # The recorded feature branch landed on origin, pointing at the feature commit.
    assert _origin_has_branch(repo, "detached-feature")
    feature_head = repo.git("rev-parse", "detached-feature", cwd=wt).strip()
    origin_head = repo.git("rev-parse", "refs/heads/detached-feature", cwd=repo.origin).strip()
    assert origin_head == feature_head
    assert parse_pr_url(read_blackboard(ticket)) == "https://github.com/acme/repo/pull/9"


def _origin_has_branch(repo, branch: str) -> bool:
    out = repo.git("branch", "--list", branch, cwd=repo.origin)
    return bool(out.strip())
