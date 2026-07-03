from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from coga import branchsweep as bs
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

    Also drops a minimal `coga/coga.toml` so `load_config` resolves with the
    default control branch `main` and remote `origin`.
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


def _cfg(repo: Path):
    return load_config(repo / "coga")


def _push_branch(repo: Path, branch: str, *, land_in_main: bool = False) -> None:
    _git(repo, "checkout", "-b", branch)
    _commit(repo, f"{branch}.txt", branch, f"{branch} work")
    _git(repo, "push", "-u", "origin", branch)
    if land_in_main:
        _git(repo, "checkout", "main")
        _git(repo, "merge", "--ff-only", branch)
        _git(repo, "push", "origin", "main")
    else:
        _git(repo, "checkout", "main")


def _remote_url(repo: Path) -> str:
    return _git(repo, "remote", "get-url", "origin").stdout.strip()


def _write_ticket(repo: Path, slug: str, *, status: str, branch: str) -> None:
    task_dir = repo / "coga" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{slug}.md").write_text(
        dedent(
            f"""
            ---
            slug: {slug}
            title: {slug}
            status: {status}
            autonomy: interactive
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

            ## Dev
            branch: {branch}
            """
        ).lstrip()
    )


def _branch_exists_local(repo: Path, branch: str) -> bool:
    return (
        _git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode
        == 0
    )


def _branch_exists_remote(repo: Path, branch: str) -> bool:
    out = _git(repo, "ls-remote", "--heads", "origin", branch).stdout.strip()
    return bool(out)


def test_merged_branch_deleted_local_and_remote(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    monkeypatch.setattr(bs, "branch_merged_without_open_pr", lambda branch, tip: True)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")


def test_open_pr_branch_skipped(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    monkeypatch.setattr(bs, "branch_merged_without_open_pr", lambda branch, tip: False)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_no_pr_branch_skipped(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")

    # No PR at all → gh reports no merged and no open PRs, which is a
    # legitimate (non-error) `False` from `branch_merged_without_open_pr`.
    monkeypatch.setattr(bs, "branch_merged_without_open_pr", lambda branch, tip: False)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_live_ticket_branch_skipped_even_if_merged(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _write_ticket(repo, "in-flight", status="in_progress", branch="feat")

    def _boom(branch: str, tip: str) -> bool:
        raise AssertionError("gh must not be consulted for a live ticket's branch")

    monkeypatch.setattr(bs, "branch_merged_without_open_pr", _boom)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_done_ticket_branch_not_protected(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _write_ticket(repo, "finished", status="done", branch="feat")
    monkeypatch.setattr(bs, "branch_merged_without_open_pr", lambda branch, tip: True)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]


def test_never_deletes_control_branch(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        bs,
        "branch_merged_without_open_pr",
        lambda branch, tip: (_ for _ in ()).throw(
            AssertionError("must not check PR for main")
        ),
    )
    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)
    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "main")


def test_checked_out_branch_left_in_place(repo: Path, monkeypatch) -> None:
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "feat.txt", "feat", "feat work")
    monkeypatch.setattr(bs, "branch_merged_without_open_pr", lambda branch, tip: True)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert _branch_exists_local(repo, "feat")


def test_gh_unavailable_no_deletes(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _push_branch(repo, "other")

    def _boom(branch: str, tip: str) -> bool:
        raise bs.GhError("`gh` not found on PATH")

    monkeypatch.setattr(bs, "branch_merged_without_open_pr", _boom)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert result.gh_unavailable is not None
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_local(repo, "other")


def test_reused_branch_requires_current_tip(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    old_tip = _git(repo, "rev-parse", "feat").stdout.strip()
    _git(repo, "checkout", "feat")
    _commit(repo, "feat-again.txt", "feat again", "reused feat")
    _git(repo, "push", "origin", "feat")
    _git(repo, "checkout", "main")

    def fake_prs(branch: str, state: str) -> list[dict[str, object]]:
        assert branch == "feat"
        if state == "merged":
            return [{"number": 7, "headRefOid": old_tip}]
        return []

    monkeypatch.setattr(bs, "_gh_prs", fake_prs)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_remote_only_branch_deleted_from_live_remote_listing(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    other = tmp_path / "other"
    subprocess.run(
        ["git", "clone", _remote_url(repo), str(other)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(other, "config", "user.email", "t@example.com")
    _git(other, "config", "user.name", "Tester")
    _push_branch(other, "remote-only")

    assert (
        _git(
            repo,
            "rev-parse",
            "--verify",
            "--quiet",
            "refs/remotes/origin/remote-only",
            check=False,
        ).returncode
        != 0
    )
    monkeypatch.setattr(bs, "branch_merged_without_open_pr", lambda branch, tip: True)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.remote_deleted == ["remote-only"]
    assert not _branch_exists_remote(repo, "remote-only")


def test_branch_merged_without_open_pr(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_prs(branch: str, state: str) -> list[dict[str, object]]:
        calls.append((branch, state))
        if state == "merged":
            return [{"number": 7, "headRefOid": "abc"}]
        return []

    monkeypatch.setattr(bs, "_gh_prs", fake_prs)
    assert bs.branch_merged_without_open_pr("feat", "abc") is True
    assert ("feat", "merged") in calls
    assert ("feat", "open") in calls


def test_branch_merged_without_open_pr_false_when_reopened(monkeypatch) -> None:
    def fake_prs(branch: str, state: str) -> list[dict[str, object]]:
        return [{"number": 7, "headRefOid": "abc"}] if state in ("merged", "open") else []

    monkeypatch.setattr(bs, "_gh_prs", fake_prs)
    assert bs.branch_merged_without_open_pr("feat", "abc") is False


def test_branch_merged_without_open_pr_false_when_tip_differs(monkeypatch) -> None:
    def fake_prs(branch: str, state: str) -> list[dict[str, object]]:
        if state == "merged":
            return [{"number": 7, "headRefOid": "old"}]
        return []

    monkeypatch.setattr(bs, "_gh_prs", fake_prs)
    assert bs.branch_merged_without_open_pr("feat", "current") is False
