"""Tests for per-task feature worktrees (`relay.git` worktree helpers)."""

from __future__ import annotations

from pathlib import Path

import pytest

from relay import git
from relay.git import GitError


def test_worktree_path_is_deterministic():
    top = Path("/repo")
    assert git.worktree_path(top, "my-task") == top / "worktree" / "my-task"


def test_create_worktree_makes_dir_and_branch(git_repo):
    path, branch = git.create_worktree(git_repo.root, "demo-task")
    assert path == git_repo.root / "worktree" / "demo-task"
    assert path.is_dir()
    assert branch == "demo-task"
    assert "demo-task" in git_repo.git("branch", "--list", "demo-task")
    assert str(path) in git_repo.git("worktree", "list")


def test_create_worktree_is_idempotent(git_repo):
    p1, b1 = git.create_worktree(git_repo.root, "demo-task")
    p2, b2 = git.create_worktree(git_repo.root, "demo-task")
    assert (p1, b1) == (p2, b2)


def test_create_worktree_custom_branch(git_repo):
    _, branch = git.create_worktree(git_repo.root, "demo-task", branch="feature/x")
    assert branch == "feature/x"
    assert "feature/x" in git_repo.git("branch", "--list", "feature/x")


def test_remove_worktree_clean(git_repo):
    git.create_worktree(git_repo.root, "demo-task")
    assert git.remove_worktree(git_repo.root, "demo-task") is True
    assert not (git_repo.root / "worktree" / "demo-task").exists()


def test_remove_worktree_absent_is_noop(git_repo):
    assert git.remove_worktree(git_repo.root, "never-made") is False


def test_remove_worktree_refuses_dirty(git_repo):
    """The guard: a worktree with untracked/uncommitted work is NOT removed,
    and we never fall back to --force."""
    path, _ = git.create_worktree(git_repo.root, "demo-task")
    (path / "scratch.txt").write_text("uncommitted work")
    with pytest.raises(GitError):
        git.remove_worktree(git_repo.root, "demo-task")
    # still there — the in-flight work was protected
    assert path.exists()
    assert (path / "scratch.txt").exists()
