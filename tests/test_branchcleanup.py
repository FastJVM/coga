from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coga.branchcleanup import delete_ticket_branch
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

    Also drops a minimal `coga-os/coga.toml` so `load_config` resolves with
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

    coga_os = root / "coga-os"
    coga_os.mkdir()
    (coga_os / "coga.toml").write_text('version = 1\ndefault_status = "draft"\n')
    (coga_os / "coga.local.toml").write_text('user = "marc"\n[slack]\nenabled = false\n')

    _commit(root, "base.txt", "base", "base")
    _git(root, "push", "-u", "origin", "main")
    return root


def _cfg(repo: Path):
    return load_config(repo / "coga-os")


def _dev_blackboard(branch: str | None = None, pr: str | None = None) -> str:
    lines = ["", "## Dev"]
    if branch is not None:
        lines.append(f"branch: {branch}")
    if pr is not None:
        lines.append(f"pr: {pr}")
    lines.append("")
    return "\n".join(lines)


def _branch_exists_local(repo: Path, branch: str) -> bool:
    return (
        _git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode
        == 0
    )


def _branch_exists_remote(repo: Path, branch: str) -> bool:
    out = _git(repo, "ls-remote", "--heads", "origin", branch).stdout.strip()
    return bool(out)


def test_clean_merge_deletes_local_and_remote(repo: Path, monkeypatch) -> None:
    # feat is merged into main (fast-forward), so `git branch -d` accepts it.
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "feat", "feat work")
    _git(repo, "push", "-u", "origin", "feat")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--ff-only", "feat")
    _git(repo, "push", "origin", "main")

    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda url: "MERGED")

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

    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda url: "MERGED")
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
