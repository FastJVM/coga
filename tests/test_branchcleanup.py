from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coga.branchcleanup import delete_ticket_branch, remove_ticket_worktree
from coga.config import load_config


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True
    )
    if check:
        assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc


def _commit(root: Path, name: str, content: str, message: str) -> None:
    (root / name).write_text(content)
    _git(root, "add", name)
    _git(root, "commit", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git working tree on `main` with a pushable bare `origin`.

    Also drops a minimal `coga/coga.toml` so `load_config` resolves with
    the default control branch `main` and remote `origin`.
    """
    remote = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(remote)],
        capture_output=True,
        text=True,
        check=True,
    )
    root = tmp_path / "work"
    root.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", str(root)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Tester")
    _git(root, "remote", "add", "origin", str(remote))

    coga_os = root / "coga"
    coga_os.mkdir()
    (coga_os / "coga.toml").write_text('version = 1\ndefault_status = "draft"\n')
    (coga_os / "coga.local.toml").write_text('user = "marc"\n[slack]\nenabled = false\n')

    _commit(root, "base.txt", "base", "base")
    _git(root, "push", "-u", "origin", "main")
    return root


@pytest.fixture(autouse=True)
def no_open_head_prs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most cleanup cases model a branch with no remaining open PR."""
    monkeypatch.setattr(
        "coga.branchcleanup.prs_for_head",
        lambda _branch, _state: [],
    )


def _cfg(repo: Path):
    return load_config(repo / "coga")


def _dev_blackboard(
    branch: str | None = None,
    pr: str | None = None,
    worktree: str | None = None,
) -> str:
    lines = ["", "## Dev"]
    if branch is not None:
        lines.append(f"branch: {branch}")
    if worktree is not None:
        lines.append(f"worktree: {worktree}")
    if pr is not None:
        lines.append(f"pr: {pr}")
    lines.append("")
    return "\n".join(lines)


def _branch_exists_local(repo: Path, branch: str) -> bool:
    return (
        _git(
            repo,
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/heads/{branch}",
            check=False,
        ).returncode
        == 0
    )


def _branch_exists_remote(repo: Path, branch: str) -> bool:
    out = _git(repo, "ls-remote", "--heads", "origin", branch).stdout.strip()
    return bool(out)


def _stub_merged_pr(monkeypatch, repo: Path, branch: str) -> str:
    tip = _git(repo, "rev-parse", branch).stdout.strip()
    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda _url: "MERGED")
    monkeypatch.setattr(
        "coga.branchcleanup.pr_head", lambda _url: (branch, tip)
    )
    return tip


def test_clean_merge_deletes_local_and_remote(repo: Path, monkeypatch) -> None:
    # feat is merged into main (fast-forward), so `git branch -d` accepts it.
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "feat", "feat work")
    _git(repo, "push", "-u", "origin", "feat")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--ff-only", "feat")
    _git(repo, "push", "origin", "main")

    _stub_merged_pr(monkeypatch, repo, "feat")

    result = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", "https://github.com/o/r/pull/7"),
        echo=lambda _m: None,
    )

    assert result.local_deleted is True
    assert result.remote_deleted is True
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")


def test_squash_merge_force_deletes_local_and_logs_tip(repo: Path, monkeypatch) -> None:
    # Squash-merge shape: the branch tip is NOT an ancestor of main (main got an
    # independent equivalent commit), so `git branch -d` refuses. The merged-PR
    # gate authorizes the forced delete; the tip SHA is reported for recovery.
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "feat", "feat work")
    _git(repo, "push", "-u", "origin", "feat")
    tip = _git(repo, "rev-parse", "feat").stdout.strip()
    _git(repo, "checkout", "main")
    _commit(repo, "feat.txt", "feat", "squashed feat")  # equivalent, different SHA
    _git(repo, "push", "origin", "main")

    _stub_merged_pr(monkeypatch, repo, "feat")
    notes: list[str] = []
    result = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", "https://github.com/o/r/pull/7"),
        echo=notes.append,
    )

    assert result.local_deleted is True
    assert result.remote_deleted is True
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")
    # The tip SHA is logged so the force-deleted local branch is recoverable.
    assert any(tip[:12] in note for note in notes), notes


def test_merged_pr_does_not_delete_branch_that_advanced_after_merge(
    repo: Path, monkeypatch
) -> None:
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "merged", "merged work")
    merged_head = _git(repo, "rev-parse", "feat").stdout.strip()
    _git(repo, "push", "-u", "origin", "feat")
    _commit(repo, "later.txt", "later", "reuse branch")
    _git(repo, "push", "origin", "feat")
    _git(repo, "checkout", "main")
    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda _url: "MERGED")
    monkeypatch.setattr(
        "coga.branchcleanup.pr_head",
        lambda _url: ("feat", merged_head),
    )

    notes: list[str] = []
    result = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", "https://github.com/o/r/pull/7"),
        echo=notes.append,
    )

    assert result.local_deleted is False
    assert result.remote_deleted is False
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert any("advanced past the merged PR head" in note for note in notes)


def test_landed_local_cleanup_preserves_remote_that_advanced_after_merge(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "merged", "merged work")
    merged_head = _git(repo, "rev-parse", "feat").stdout.strip()
    _git(repo, "push", "-u", "origin", "feat")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--ff-only", "feat")
    _git(repo, "push", "origin", "main")

    other = tmp_path / "other"
    subprocess.run(
        ["git", "clone", str(repo.parent / "origin.git"), str(other)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(other, "config", "user.email", "t@example.com")
    _git(other, "config", "user.name", "Tester")
    _git(other, "checkout", "feat")
    _commit(other, "later.txt", "later", "reuse branch remotely")
    _git(other, "push", "origin", "feat")

    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda _url: "MERGED")
    monkeypatch.setattr(
        "coga.branchcleanup.pr_head",
        lambda _url: ("feat", merged_head),
    )

    result = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", "https://github.com/o/r/pull/7"),
        echo=lambda _m: None,
    )

    assert result.local_deleted is True
    assert result.remote_deleted is False
    assert not _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_unmerged_no_pr_is_skipped(repo: Path, monkeypatch) -> None:
    # Pushed branch, tip not landed in main, no `pr:` line → never delete; the
    # work is unmerged and we have no merged-PR signal authorizing removal. This
    # is the case `git branch -d` alone gets wrong (it would delete on the
    # strength of the branch being pushed to its upstream).
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "feat", "unmerged feat")
    _git(repo, "push", "-u", "origin", "feat")
    _git(repo, "checkout", "main")

    # No `pr:` line → pr_state is never consulted; assert that by exploding if it is.
    def _boom(url: str) -> str:
        raise AssertionError("pr_state should not be called without a pr: line")

    monkeypatch.setattr("coga.branchcleanup.pr_state", _boom)

    result = delete_ticket_branch(
        _cfg(repo), repo, _dev_blackboard("feat"), echo=lambda _m: None
    )

    assert result.local_deleted is False
    assert result.remote_deleted is False
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_unmerged_pr_open_skips_both(repo: Path, monkeypatch) -> None:
    # PR exists but is OPEN (not merged) → both deletes skip.
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "feat", "unmerged feat")
    _git(repo, "push", "-u", "origin", "feat")
    _git(repo, "checkout", "main")

    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda url: "OPEN")
    result = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", "https://github.com/o/r/pull/7"),
        echo=lambda _m: None,
    )

    assert result.local_deleted is False
    assert result.remote_deleted is False
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_other_open_head_pr_preserves_landed_local_and_remote_branches(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "feat", "feat work")
    _git(repo, "push", "-u", "origin", "feat")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--ff-only", "feat")

    monkeypatch.setattr(
        "coga.branchcleanup.prs_for_head",
        lambda branch, state: (
            [{"number": 12, "headRefOid": "unused"}]
            if branch == "feat" and state == "open"
            else []
        ),
    )
    notes: list[str] = []

    result = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", "https://github.com/o/r/pull/7"),
        echo=notes.append,
    )

    assert result.local_deleted is False
    assert result.remote_deleted is False
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert any("still has 1 open PR (#12)" in note for note in notes)


def test_never_deletes_control_branch(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "coga.branchcleanup.pr_state",
        lambda url: (_ for _ in ()).throw(AssertionError("must not check PR for main")),
    )
    result = delete_ticket_branch(
        _cfg(repo), repo, _dev_blackboard("main"), echo=lambda _m: None
    )
    assert result.local_deleted is False
    assert result.remote_deleted is False
    assert _branch_exists_local(repo, "main")


def test_no_branch_line_is_noop(repo: Path) -> None:
    result = delete_ticket_branch(
        _cfg(repo), repo, "## Dev\npr: https://github.com/o/r/pull/1\n", echo=lambda _m: None
    )
    assert result.branch is None
    assert result.local_deleted is False
    assert result.remote_deleted is False


def _add_worktree(repo: Path, path: Path, branch: str) -> None:
    _git(repo, "worktree", "add", str(path), "-b", branch)


def test_removes_recorded_linked_worktree(repo: Path, tmp_path: Path) -> None:
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")

    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=lambda _m: None,
    )

    assert result.worktree == str(feature)
    assert result.removed is True
    assert not feature.exists()
    assert "feat" not in _git(repo, "worktree", "list").stdout


def test_open_head_pr_preserves_landed_worktree(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")
    _commit(feature, "feat.txt", "feat", "feat work")
    _git(repo, "merge", "--ff-only", "feat")
    monkeypatch.setattr(
        "coga.branchcleanup.prs_for_head",
        lambda branch, state: (
            [{"number": 12, "headRefOid": "unused"}]
            if branch == "feat" and state == "open"
            else []
        ),
    )
    notes: list[str] = []

    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=notes.append,
    )

    assert result.removed is False
    assert feature.is_dir()
    assert any("still has 1 open PR (#12)" in note for note in notes)


def test_control_tag_cannot_make_unmerged_worktree_look_landed(
    repo: Path, tmp_path: Path
) -> None:
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")
    _commit(feature, "feat.txt", "feat", "unmerged feat")
    # A loose ref named like the configured control branch used to make
    # `merge-base ... feat main` resolve the tag and authorize removal.
    _git(repo, "tag", "main", "refs/heads/feat")
    notes: list[str] = []

    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=notes.append,
    )

    assert result.removed is False
    assert feature.is_dir()
    assert any("has not landed on 'main'" in note for note in notes)


def test_removing_worktree_unpins_branch_for_cleanup(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    """The compounding bug: a worktree-held branch cannot be deleted at all."""
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")
    _commit(feature, "feat.txt", "feat", "feat work")
    _git(repo, "merge", "--ff-only", "feat")
    # Without the worktree removal, git refuses: "used by worktree at ...".
    pinned = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=lambda _m: None,
    )
    assert pinned.local_deleted is False
    assert _branch_exists_local(repo, "feat")

    remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=lambda _m: None,
    )
    freed = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=lambda _m: None,
    )

    assert freed.local_deleted is True
    assert not _branch_exists_local(repo, "feat")


def test_dirty_worktree_left_in_place(repo: Path, tmp_path: Path) -> None:
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")
    (feature / "uncommitted.txt").write_text("work in progress")

    notes: list[str] = []
    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=notes.append,
    )

    assert result.removed is False
    assert feature.is_dir()
    assert (feature / "uncommitted.txt").is_file()
    assert any("contains tracked, untracked, or ignored" in note for note in notes)


def test_ignored_local_file_left_in_place(repo: Path, tmp_path: Path) -> None:
    (repo / ".gitignore").write_text("*.secret\n")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "ignore local secrets")
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")
    (feature / "credentials.secret").write_text("do not delete")

    notes: list[str] = []
    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=notes.append,
    )

    assert result.removed is False
    assert (feature / "credentials.secret").read_text() == "do not delete"
    assert any("ignored local state" in note for note in notes)


def test_worktree_holding_another_branch_left_in_place(
    repo: Path, tmp_path: Path
) -> None:
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "other-ticket")

    notes: list[str] = []
    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("retiring-ticket", worktree=str(feature)),
        echo=notes.append,
    )

    assert result.removed is False
    assert feature.is_dir()
    assert any(
        "holds 'other-ticket', not the recorded branch 'retiring-ticket'" in note
        for note in notes
    )


def test_worktree_advanced_past_recorded_merged_pr_is_left_in_place(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")
    merged_head = _git(repo, "rev-parse", "main").stdout.strip()
    _commit(feature, "new.txt", "new work", "reuse branch")
    _git(feature, "push", "-u", "origin", "feat")
    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda _url: "MERGED")
    monkeypatch.setattr(
        "coga.branchcleanup.pr_head",
        lambda _url: ("feat", merged_head),
    )

    notes: list[str] = []
    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard(
            "feat",
            "https://github.com/o/r/pull/7",
            worktree=str(feature),
        ),
        echo=notes.append,
    )

    assert result.removed is False
    assert feature.is_dir()
    assert any("advanced past the merged PR head" in note for note in notes)


def test_independent_clone_left_in_place(repo: Path, tmp_path: Path) -> None:
    """The sandbox fallback checkout is a clone, not a linked worktree."""
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--no-hardlinks", str(repo), str(clone)],
        capture_output=True,
        text=True,
        check=True,
    )

    notes: list[str] = []
    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(clone)),
        echo=notes.append,
    )

    assert result.removed is False
    assert clone.is_dir()
    assert any("not a linked worktree" in note for note in notes)


def test_primary_checkout_left_in_place(repo: Path) -> None:
    notes: list[str] = []
    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(repo)),
        echo=notes.append,
    )

    assert result.removed is False
    assert repo.is_dir()
    assert any("checkout running retire" in note for note in notes)


def test_retire_checkout_cannot_remove_itself(
    repo: Path, tmp_path: Path
) -> None:
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")

    notes: list[str] = []
    result = remove_ticket_worktree(
        _cfg(repo),
        feature,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=notes.append,
    )

    assert result.removed is False
    assert feature.is_dir()
    assert any("checkout running retire" in note for note in notes)


def test_missing_worktree_path_is_reported_not_pruned(
    repo: Path, tmp_path: Path
) -> None:
    feature = tmp_path / "feature"
    _add_worktree(repo, feature, "feat")
    subprocess.run(["rm", "-rf", str(feature)], check=True)

    notes: list[str] = []
    result = remove_ticket_worktree(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", worktree=str(feature)),
        echo=notes.append,
    )

    assert result.removed is False
    assert any("already gone" in note for note in notes)
    # The stale registration is branch sweep's repo-wide job, not retire's.
    assert str(feature) in _git(repo, "worktree", "list").stdout


def test_no_worktree_line_is_noop(repo: Path) -> None:
    result = remove_ticket_worktree(
        _cfg(repo), repo, _dev_blackboard("feat"), echo=lambda _m: None
    )
    assert result.worktree is None
    assert result.removed is False


def test_checked_out_branch_left_in_place(repo: Path, monkeypatch) -> None:
    # If retire is somehow run while the feature branch is checked out, refuse.
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "feat", "feat work")
    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda url: "MERGED")
    result = delete_ticket_branch(
        _cfg(repo),
        repo,
        _dev_blackboard("feat", "https://github.com/o/r/pull/7"),
        echo=lambda _m: None,
    )
    assert result.local_deleted is False
    assert _branch_exists_local(repo, "feat")
