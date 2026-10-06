from __future__ import annotations

import shutil
import runpy
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from coga import branchsweep as bs
from coga.config import load_config
from coga.skill_manager import SKILL_UPDATE_BRANCH


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
    (coga_os / "coga.local.toml").write_text(
        'user = "marc"\n[notification.slack]\nenabled = false\n'
    )

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


def _tip(repo: Path, ref: str) -> str:
    return _git(repo, "rev-parse", ref).stdout.strip()


def _fake_gh(
    monkeypatch,
    merged: dict[str, str] | None = None,
    *,
    open_heads: frozenset[str] = frozenset(),
    closed: dict[str, str] | None = None,
) -> None:
    """Stub `gh pr list --head`: `merged` maps a branch to its merged head SHA.

    `closed` maps a branch to the head of a PR closed without merging. Like
    real `gh --state closed`, the closed listing also returns merged PRs.
    """
    heads = merged or {}
    closed_heads = closed or {}

    def fake_prs(branch: str, state: str) -> list[dict[str, object]]:
        if state == "merged" and branch in heads:
            return [{"number": 7, "headRefOid": heads[branch]}]
        if state == "open" and branch in open_heads:
            return [{"number": 8, "headRefOid": heads.get(branch, "")}]
        if state == "closed":
            prs: list[dict[str, object]] = []
            if branch in heads:
                prs.append({"number": 7, "headRefOid": heads[branch]})
            if branch in closed_heads:
                prs.append({"number": 9, "headRefOid": closed_heads[branch]})
            return prs
        return []

    monkeypatch.setattr(bs, "prs_for_head", fake_prs)


def _merged_at_tip(monkeypatch, repo: Path, *branches: str) -> None:
    """Stub gh so each branch's current local tip is a merged PR head."""
    _fake_gh(monkeypatch, {branch: _tip(repo, branch) for branch in branches})


def _ticket_text(slug: str, *, status: str, body: str, blackboard: str) -> str:
    # Dedent the template first: a multi-line `body` or `blackboard` would
    # otherwise defeat `dedent` and leave the frontmatter indented.
    template = dedent(
        """
        ---
        title: SLUG
        status: STATUS
        autonomy: interactive
        owner: marc
        agent: claude
        workflow: null
        ---

        ## Description

        BODY

        <!-- coga:blackboard -->

        BLACKBOARD
        """
    ).lstrip()
    return (
        template.replace("SLUG", slug)
        .replace("STATUS", status)
        .replace("BODY", body)
        .replace("BLACKBOARD", blackboard)
    )


def _write_ticket(repo: Path, slug: str, *, status: str, branch: str) -> None:
    task_dir = repo / "coga" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{slug}.md").write_text(
        _ticket_text(
            slug, status=status, body="", blackboard=f"## Dev\nbranch: {branch}"
        )
    )


def _squash_merge(repo: Path, branch: str) -> None:
    """Land `branch` on main the way GitHub's squash button does."""
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--squash", branch)
    _git(repo, "commit", "-m", f"{branch} (#7)")
    _git(repo, "push", "origin", "main")


def _state_commit(repo: Path, branch: str, name: str) -> None:
    """One Coga state-sync commit on `branch`: a task file plus the audit log."""
    _git(repo, "checkout", branch)
    tasks = repo / "coga" / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    (tasks / f"{name}.md").write_text(f"state {name}\n")
    log = repo / "coga" / "log.md"
    with log.open("a") as handle:
        handle.write(f"log {name}\n")
    _git(repo, "add", "coga/tasks", "coga/log.md")
    _git(repo, "commit", "-m", f"Ticket: {name} — done")


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
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")


def test_shared_skill_update_branch_survives_without_a_ticket_or_open_pr(
    repo: Path, monkeypatch
) -> None:
    _git(repo, "branch", SKILL_UPDATE_BRANCH)
    _git(repo, "push", "origin", SKILL_UPDATE_BRANCH)
    monkeypatch.setattr(bs, "prs_for_head", _gh_must_not_be_consulted)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, SKILL_UPDATE_BRANCH)
    assert _branch_exists_remote(repo, SKILL_UPDATE_BRANCH)
    assert any("shared skill-update branch" in note for note in result.notes)


def test_retirement_tag_is_pushed_before_any_ref_is_deleted(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    tip = _tip(repo, "feat")
    _merged_at_tip(monkeypatch, repo, "feat")
    real_delete = bs.delete_local_branch

    def delete_after_archive(*args, **kwargs):
        assert _tip(repo, "refs/tags/retired/feat") == tip
        assert _git(repo, "ls-remote", "--tags", "origin", "refs/tags/retired/feat").stdout.split()[0] == tip
        assert _branch_exists_remote(repo, "feat")
        return real_delete(*args, **kwargs)

    monkeypatch.setattr(bs, "delete_local_branch", delete_after_archive)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == ["feat"]
    assert result.failure is None


def test_retirement_push_does_not_publish_unrelated_follow_tags(
    repo: Path, monkeypatch
) -> None:
    _git(repo, "branch", "feat")
    _git(repo, "tag", "-a", "unpublished-release", "-m", "Not ready to publish")
    _git(repo, "config", "push.followTags", "true")
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    tags = _git(repo, "ls-remote", "--tags", "origin").stdout
    assert "refs/tags/retired/feat" in tags
    assert "unpublished-release" not in tags


@pytest.mark.parametrize("with_worktree", [False, True])
def test_failed_tag_push_preserves_both_refs_and_reports_failure(
    repo: Path, monkeypatch, capsys, with_worktree: bool
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    linked = repo.parent / "linked"
    if with_worktree:
        _git(repo, "worktree", "add", str(linked), "feat")
        _own_worktrees(repo)
    _merged_at_tip(monkeypatch, repo, "feat")
    real_git = bs._git

    def fail_tag_push(root: Path, *args: str, input: str | None = None):
        if args[0] == "push" and any("refs/tags/retired/feat" in arg for arg in args):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="tag push rejected")
        return real_git(root, *args, input=input)

    monkeypatch.setattr(bs, "_git", fail_tag_push)

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 2

    output = capsys.readouterr()
    assert "tag push rejected" in output.out
    assert "retired/feat" in output.err
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    if with_worktree:
        assert linked.is_dir()


def _remote_tag(repo: Path, name: str) -> str:
    out = _git(repo, "ls-remote", "--tags", "origin", f"refs/tags/{name}").stdout
    return out.split()[0] if out else ""


@pytest.mark.parametrize("where", ["local", "remote"])
def test_conflicting_retirement_tag_is_kept_and_tip_archived_under_its_sha(
    repo: Path, monkeypatch, where: str
) -> None:
    original = _tip(repo, "main")
    _git(repo, "tag", "retired/feat", original)
    if where == "remote":
        _git(repo, "push", "origin", "refs/tags/retired/feat")
        _git(repo, "tag", "-d", "retired/feat")
    _push_branch(repo, "feat", land_in_main=True)
    tip = _tip(repo, "feat")
    _merged_at_tip(monkeypatch, repo, "feat")

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 0

    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")
    if where == "local":
        assert _tip(repo, "refs/tags/retired/feat") == original
        assert _remote_tag(repo, "retired/feat") == ""
    else:
        assert _remote_tag(repo, "retired/feat") == original
    assert _remote_tag(repo, f"retired/feat@{tip[:12]}") == tip
    assert _tip(repo, f"refs/tags/retired/feat@{tip[:12]}") == tip


@pytest.mark.parametrize("where", ["local", "remote"])
@pytest.mark.parametrize("object_ref", ["main:base.txt", "main^{tree}"])
@pytest.mark.parametrize("annotated", [False, True])
def test_non_commit_retirement_tag_uses_sha_fallback(
    repo: Path, monkeypatch, where: str, object_ref: str, annotated: bool
) -> None:
    tag_repo = repo if where == "local" else Path(_remote_url(repo))
    tag_args = ["-a", "-m", "Non-commit archive"] if annotated else []
    _git(
        tag_repo, "-c", "user.name=Tester", "-c", "user.email=t@example.com",
        "tag", *tag_args, "retired/feat", object_ref,
    )
    original = _tip(tag_repo, "refs/tags/retired/feat")
    _push_branch(repo, "feat", land_in_main=True)
    tip = _tip(repo, "feat")
    _merged_at_tip(monkeypatch, repo, "feat")

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 0

    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")
    assert _tip(tag_repo, "refs/tags/retired/feat") == original
    if where == "local":
        assert _remote_tag(repo, "retired/feat") == ""
    else:
        assert _git(
            repo, "show-ref", "--verify", "refs/tags/retired/feat", check=False
        ).returncode != 0
    assert _remote_tag(repo, f"retired/feat@{tip[:12]}") == tip
    assert _tip(repo, f"refs/tags/retired/feat@{tip[:12]}") == tip


def test_unavailable_remote_tag_object_still_refuses_retirement(
    repo: Path, monkeypatch
) -> None:
    remote = Path(_remote_url(repo))
    _git(
        remote, "-c", "user.name=Tester", "-c", "user.email=t@example.com",
        "tag", "-a", "-m", "Remote-only tag", "retired/feat", "main:base.txt",
    )
    original = _tip(remote, "refs/tags/retired/feat")
    _push_branch(repo, "feat", land_in_main=True)
    tip = _tip(repo, "feat")
    _merged_at_tip(monkeypatch, repo, "feat")
    real_git = bs._git

    def fail_archive_fetch(root: Path, *args: str, input: str | None = None):
        if args[0] == "fetch" and args[-1] == original:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="fetch failed")
        return real_git(root, *args, input=input)

    monkeypatch.setattr(bs, "_git", fail_archive_fetch)

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 2

    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert _remote_tag(repo, "retired/feat") == original
    assert _remote_tag(repo, f"retired/feat@{tip[:12]}") == ""


def test_retirement_tag_containing_the_tip_counts_as_archived(
    repo: Path, monkeypatch
) -> None:
    # Another clone archived the merged head; this clone still holds an
    # earlier tip and the stale local tag an earlier failed pass left behind.
    _push_branch(repo, "feat")
    stale = _tip(repo, "feat")
    _git(repo, "checkout", "feat")
    _commit(repo, "more.txt", "more", "more work")
    merged_head = _tip(repo, "feat")
    _git(repo, "push", "origin", "feat")
    _git(repo, "push", "origin", f"{merged_head}:refs/tags/retired/feat")
    _git(repo, "push", "origin", "--delete", "feat")
    _squash_merge(repo, "feat")
    _git(repo, "branch", "-f", "feat", stale)
    _git(repo, "update-ref", "-d", "refs/remotes/origin/feat")
    _git(repo, "tag", "retired/feat", stale)
    _fake_gh(monkeypatch, {"feat": merged_head})
    real_git = bs._git

    def no_tag_push(root: Path, *args: str, input: str | None = None):
        assert not (args[0] == "push" and any("refs/tags/" in arg for arg in args))
        return real_git(root, *args, input=input)

    monkeypatch.setattr(bs, "_git", no_tag_push)

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 0

    assert not _branch_exists_local(repo, "feat")
    assert _remote_tag(repo, "retired/feat") == merged_head
    assert _tip(repo, "refs/tags/retired/feat") == merged_head


@pytest.mark.parametrize("object_ref", ["main", "main:base.txt", "main^{tree}"])
def test_both_retirement_names_taken_fails_without_overwriting(
    repo: Path, monkeypatch, object_ref: str
) -> None:
    original = _tip(repo, object_ref)
    _push_branch(repo, "feat", land_in_main=True)
    tip = _tip(repo, "feat")
    for name in ("retired/feat", f"retired/feat@{tip[:12]}"):
        _git(repo, "push", "origin", f"{original}:refs/tags/{name}")
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.failure is not None
    assert "already archive other objects" in result.failure
    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _remote_tag(repo, f"retired/feat@{tip[:12]}") == original


def test_sha_qualified_retirement_tag_allows_retry(repo: Path, monkeypatch) -> None:
    original = _tip(repo, "main")
    _git(repo, "push", "origin", f"{original}:refs/tags/retired/feat")
    _push_branch(repo, "feat", land_in_main=True)
    tip = _tip(repo, "feat")
    _git(repo, "push", "origin", f"{tip}:refs/tags/retired/feat@{tip[:12]}")
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.failure is None
    assert result.local_deleted == result.remote_deleted == ["feat"]
    assert any("already archived" in note for note in result.notes)


def test_existing_retirement_tag_allows_retry(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _git(repo, "tag", "retired/feat", "feat")
    _git(repo, "push", "origin", "refs/tags/retired/feat")
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.failure is None
    assert result.local_deleted == result.remote_deleted == ["feat"]


def test_partial_cleanup_retry_trusts_archive_containing_remote_tip(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    merged_head = _tip(repo, "feat")
    _state_commit(repo, "feat", "later-bookkeeping")
    archived_tip = _tip(repo, "feat")
    _git(repo, "checkout", "main")
    _fake_gh(monkeypatch, {"feat": merged_head})
    with monkeypatch.context() as unavailable:
        unavailable.setattr(bs, "delete_remote_branch", lambda *args, **kwargs: None)
        first = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)
    assert first.local_deleted == ["feat"]
    assert first.remote_deleted == []

    retry = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    # The archive already contains the lagging remote tip; it is never moved.
    assert retry.failure is None
    assert retry.remote_deleted == ["feat"]
    assert _remote_tag(repo, "retired/feat") == archived_tip
    assert _tip(repo, "refs/tags/retired/feat") == archived_tip


def test_retirement_tag_named_like_another_branch_does_not_hide_it(
    repo: Path, monkeypatch
) -> None:
    _git(repo, "branch", "retired/feat")
    _push_branch(repo, "feat", land_in_main=True)
    _git(repo, "tag", "retired/feat", "refs/heads/feat")
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat", "retired/feat"]
    assert result.remote_deleted == ["feat"]
    assert not _branch_exists_local(repo, "retired/feat")


def test_local_ref_moved_after_archive_is_kept(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _merged_at_tip(monkeypatch, repo, "feat")
    archived_tip = _tip(repo, "feat")
    real_delete = bs.delete_local_branch

    def move_before_delete(*args, **kwargs):
        _commit(repo, "later.txt", "later", "later landed work")
        _git(repo, "update-ref", "refs/heads/feat", _tip(repo, "main"))
        return real_delete(*args, **kwargs)

    monkeypatch.setattr(bs, "delete_local_branch", move_before_delete)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert _tip(repo, "refs/tags/retired/feat") == archived_tip
    assert any("moved from the authorized tip" in note for note in result.notes)


def test_branch_that_lands_after_sweep_check_waits_for_archival_next_pass(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    _fake_gh(monkeypatch)

    def control_advances_after_check(*args):
        _git(repo, "merge", "--ff-only", "feat")
        return False

    monkeypatch.setattr(bs, "local_branch_landed", control_advances_after_check)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_divergent_merged_heads_are_preserved_when_one_tag_cannot_cover_both(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    merged_head = _tip(repo, "feat")
    _state_commit(repo, "feat", "local-state")
    _git(repo, "checkout", "-b", "other", merged_head)
    _state_commit(repo, "other", "remote-state")
    remote_tip = _tip(repo, "other")
    _git(repo, "push", "origin", "other:feat")
    _git(repo, "checkout", "main")
    _git(repo, "branch", "-D", "other")
    local_tip = _tip(repo, "feat")
    # Each tip is a merged PR head, so neither can be left to its PR ref.
    monkeypatch.setattr(
        bs,
        "prs_for_head",
        lambda branch, state: [
            {"number": 7, "headRefOid": local_tip},
            {"number": 9, "headRefOid": remote_tip},
        ]
        if state == "merged" and branch == "feat"
        else [],
    )

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == []
    assert result.failure is not None
    assert "divergent" in result.failure
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_open_pr_branch_skipped(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    _fake_gh(monkeypatch, {"feat": _tip(repo, "feat")}, open_heads=frozenset({"feat"}))

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_no_pr_branch_skipped(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")

    # No PR at all → gh reports no merged and no open PRs, which is a
    # legitimate (non-error) refusal from `merged_pr_verdict`.
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_live_ticket_branch_skipped_even_if_merged(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _write_ticket(repo, "in-flight", status="in_progress", branch="feat")

    monkeypatch.setattr(bs, "prs_for_head", _gh_must_not_be_consulted)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def _gh_must_not_be_consulted(branch: str, state: str) -> list[dict[str, object]]:
    raise AssertionError("gh must not be consulted for a live ticket's branch")


def test_live_ticket_prose_mention_pins_branch_without_dev_section(
    repo: Path, monkeypatch
) -> None:
    # The guard used to read only `## Dev` `branch:`; a draft that named its
    # branch three times in prose and attachments but had no `## Dev` at all
    # was invisible to it, and a merged PR at the exact tip would have
    # force-deleted the ref it still depended on.
    _push_branch(repo, "feat", land_in_main=True)
    task_dir = repo / "coga" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "prose-only.md").write_text(
        _ticket_text(
            "prose-only",
            status="draft",
            body="Follow-up commits sit unpushed on `feat` in this checkout.",
            blackboard="notes",
        )
    )
    monkeypatch.setattr(bs, "prs_for_head", _gh_must_not_be_consulted)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_live_ticket_attachment_mention_pins_branch(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    task_dir = repo / "coga" / "tasks" / "with-manifest"
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(
        _ticket_text("with-manifest", status="active", body="", blackboard="notes")
    )
    (task_dir / "handoff-manifest.md").write_text("Coga source branch: `feat`\n")
    monkeypatch.setattr(bs, "prs_for_head", _gh_must_not_be_consulted)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert _branch_exists_local(repo, "feat")


def test_live_ticket_mention_must_be_the_whole_branch_name(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    task_dir = repo / "coga" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "near-miss.md").write_text(
        _ticket_text(
            "near-miss",
            status="active",
            body="See the feature-flag branch, old-feat and feat/two, not this one.",
            blackboard="notes",
        )
    )
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]


@pytest.mark.parametrize(
    "prose",
    [
        "Follow-up commits sit unpushed on feat.",
        "Pushed to origin/feat yesterday.",
    ],
)
def test_live_ticket_prose_mention_survives_punctuation(
    repo: Path, monkeypatch, prose: str
) -> None:
    # A sentence-final period and a remote-qualified spelling are the common
    # un-backticked shapes; neither may hide the name from the guard.
    _push_branch(repo, "feat", land_in_main=True)
    task_dir = repo / "coga" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "prose.md").write_text(
        _ticket_text("prose", status="active", body=prose, blackboard="notes")
    )
    monkeypatch.setattr(bs, "prs_for_head", _gh_must_not_be_consulted)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert _branch_exists_local(repo, "feat")


def test_period_task_report_does_not_pin_the_branches_it_names(
    repo: Path, monkeypatch
) -> None:
    # A failed sweep leaves its period task `in_progress` with a report that
    # lists every branch it skipped; the resumed run must not read that as
    # "recorded on a live ticket" and refuse them all. Autoclose's retire
    # follow-ups on its own period task name leaked branches the same way.
    _push_branch(repo, "feat", land_in_main=True)
    task_dir = repo / "coga" / "tasks" / "recurring" / "branch-sweep"
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(
        _ticket_text(
            "branch-sweep",
            status="in_progress",
            body="",
            blackboard="## Branch Sweep\n\n- skipped: feat\n",
        )
    )
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]


def test_period_task_dev_branch_still_pins(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    task_dir = repo / "coga" / "tasks" / "recurring" / "weekly"
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(
        _ticket_text(
            "weekly", status="in_progress", body="", blackboard="## Dev\nbranch: feat"
        )
    )
    monkeypatch.setattr(bs, "prs_for_head", _gh_must_not_be_consulted)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert _branch_exists_local(repo, "feat")


def test_done_ticket_branch_not_protected(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _write_ticket(repo, "finished", status="done", branch="feat")
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]


def test_canceled_ticket_branch_not_protected(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _write_ticket(repo, "declined", status="canceled", branch="feat")
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]


def test_never_deletes_control_branch(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        bs,
        "prs_for_head",
        lambda branch, state: (_ for _ in ()).throw(
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
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert _branch_exists_local(repo, "feat")


def test_prunable_worktree_no_longer_pins_merged_branch(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    shutil.rmtree(linked)
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")


def test_pruned_stacked_branch_is_not_landed_by_feature_head(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "stack-base")
    _git(repo, "checkout", "stack-base")
    _git(repo, "checkout", "-b", "stack-tip")
    _commit(repo, "stack-tip.txt", "tip", "stack tip")
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "stack-base")
    shutil.rmtree(linked)
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert result.skipped == ["stack-base"]
    assert _branch_exists_local(repo, "stack-base")
    assert _branch_exists_remote(repo, "stack-base")


def test_live_worktree_pinned_merged_branch_has_distinct_outcome(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    # Squash-merge shape: the branch tip is not reachable from main, so only
    # the exact-tip GitHub signal authorizes branch cleanup.
    _push_branch(repo, "feat")
    _commit(repo, "feat.txt", "feat", "squashed feat")
    _git(repo, "push", "origin", "main")
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert result.skipped == []
    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert linked.is_dir()


def test_live_worktree_pinned_git_merged_branch_has_distinct_outcome(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert result.skipped == []
    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_rebasing_worktree_preserves_both_refs_with_distinct_outcome(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    _commit(repo, "feat.txt", "main version", "conflicting main change")
    rebase = _git(linked, "rebase", "main", check=False)
    assert rebase.returncode != 0
    listing = _git(repo, "worktree", "list", "--porcelain").stdout
    assert f"worktree {linked}\n" in listing
    assert "detached" in listing
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert result.skipped == []
    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert linked.is_dir()


def _own_worktrees(repo: Path) -> None:
    """Opt the repo into `[git].worktrees_ticket_owned`."""
    toml = repo / "coga" / "coga.toml"
    toml.write_text(toml.read_text() + "[git]\nworktrees_ticket_owned = true\n")


def test_pinning_worktree_is_removed_when_worktrees_are_ticket_owned(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    (repo / ".gitignore").write_text("__pycache__/\n")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "ignore caches")
    _push_branch(repo, "feat", land_in_main=True)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    # A test run's caches are regenerable and do not make the checkout dirty.
    (linked / "__pycache__").mkdir()
    (linked / "__pycache__" / "x.pyc").write_bytes(b"")
    _own_worktrees(repo)
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_removed == [str(linked)]
    assert result.worktree_pinned == []
    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == []  # no merged PR vouches for the remote ref
    assert not linked.exists()
    assert not _branch_exists_local(repo, "feat")
    assert any("removed linked worktree" in note for note in result.notes)


def test_pinning_worktree_stays_when_key_is_off(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert result.worktree_removed == []
    assert linked.is_dir()
    assert _branch_exists_local(repo, "feat")


def test_dirty_pinning_worktree_is_reported_not_removed(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    (linked / "scratch.txt").write_text("unsaved")
    _own_worktrees(repo)
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert result.worktree_removed == []
    assert result.local_deleted == []
    assert linked.is_dir()
    assert (linked / "scratch.txt").is_file()
    assert _branch_exists_local(repo, "feat")
    assert any(
        "contains tracked or untracked local state" in note for note in result.notes
    )
    assert any(
        "worktree" in note and "was preserved — both refs left in place" in note
        for note in result.notes
    )
    assert not _git(repo, "ls-remote", "--tags", "origin").stdout
    assert not _git(repo, "tag", "--list", "retired/feat").stdout

    # Finishing the preserved work must not conflict with a premature archive.
    _commit(linked, "scratch.txt", "finished", "finish pending work")
    _git(linked, "push", "origin", "feat")
    _git(repo, "merge", "--ff-only", "feat")
    final_tip = _tip(repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.failure is None
    assert result.worktree_removed == [str(linked)]
    assert result.local_deleted == ["feat"]
    assert _tip(repo, "refs/tags/retired/feat") == final_tip


def test_worktree_that_becomes_dirty_during_archive_is_preserved(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    _own_worktrees(repo)
    _merged_at_tip(monkeypatch, repo, "feat")
    publish = bs._publish_retirement_tag

    def publish_then_dirty(*args, **kwargs):
        archived = publish(*args, **kwargs)
        (linked / ".env").write_text("new local state")
        return archived

    # Git's unforced removal permits ignored files, so the second inspection
    # must catch newly created non-regenerable state after the network push.
    _git(repo, "config", "core.excludesFile", str(tmp_path / "gitignore"))
    (tmp_path / "gitignore").write_text(".env\n")
    monkeypatch.setattr(bs, "_publish_retirement_tag", publish_then_dirty)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert result.local_deleted == result.remote_deleted == []
    assert (linked / ".env").read_text() == "new local state"


def test_worktree_that_gains_a_clean_commit_during_archive_is_preserved(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    _own_worktrees(repo)
    _merged_at_tip(monkeypatch, repo, "feat")
    archived_tip = _tip(repo, "feat")
    publish = bs._publish_retirement_tag

    def publish_then_commit(*args, **kwargs):
        archived = publish(*args, **kwargs)
        _commit(linked, "late.txt", "unlanded work", "Late commit")
        return archived

    monkeypatch.setattr(bs, "_publish_retirement_tag", publish_then_commit)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert result.worktree_removed == []
    assert result.local_deleted == result.remote_deleted == []
    assert (linked / "late.txt").read_text() == "unlanded work"
    assert _tip(repo, "feat") != archived_tip


def test_claimed_pinning_worktree_is_reported_not_removed(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")
    # A live ticket records the *path* under another branch name, which the
    # branch-mention guard cannot see.
    task_dir = repo / "coga" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "reuses-checkout.md").write_text(
        _ticket_text(
            "reuses-checkout",
            status="in_progress",
            body="",
            blackboard=f"## Dev\nbranch: other\nworktree: {linked}",
        )
    )
    _own_worktrees(repo)
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert result.worktree_removed == []
    assert linked.is_dir()
    assert _branch_exists_local(repo, "feat")
    assert any(
        f"live ticket 'reuses-checkout' also records worktree '{linked.resolve()}'"
        in note
        for note in result.notes
    )
    assert not _git(repo, "ls-remote", "--tags", "origin").stdout
    assert not _git(repo, "tag", "--list", "retired/feat").stdout


def test_recipe_reports_removed_worktrees(repo: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(bs.git, "toplevel", lambda _root: repo)

    def _sweep(_cfg, _root, *, echo, result=None):
        result.worktree_removed.append("/w/coga-feat")
        result.local_deleted.append("feat")
        return result

    monkeypatch.setattr(bs, "sweep_branches", _sweep)

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 0

    captured = capsys.readouterr()
    assert "[branch-sweep] removed-worktree: /w/coga-feat" in captured.out
    assert "1 worktree(s) removed" in captured.out
    assert "- removed worktree: /w/coga-feat" in captured.out


def test_worktree_prune_failure_stops_sweep(repo: Path, monkeypatch) -> None:
    def fail_prune(
        root: Path, *args: str
    ) -> subprocess.CompletedProcess[str]:
        assert root == repo
        assert args == ("worktree", "prune")
        return subprocess.CompletedProcess(
            ["git", "worktree", "prune"],
            1,
            stdout="",
            stderr="permission denied",
        )

    monkeypatch.setattr(bs, "_git", fail_prune)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_unavailable == "permission denied"
    assert result.local_deleted == []
    assert result.remote_deleted == []


def test_recipe_reports_worktree_pinned_outcome(
    repo: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(bs.git, "toplevel", lambda _root: repo)

    def _sweep(_cfg, _root, *, echo, result=None):
        # Fills in the accumulator it was handed, as the real sweep does — the
        # wrapper reads the caller's object, not this function's return value.
        result.worktree_pinned.append("feat")
        return result

    monkeypatch.setattr(bs, "sweep_branches", _sweep)

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 0

    captured = capsys.readouterr()
    assert "[branch-sweep] skipped-worktree-pinned: feat" in captured.out
    assert captured.err == ""


def test_recipe_hands_back_the_deleted_branches(repo: Path, monkeypatch) -> None:
    # The wrapper already computes this result; the out-parameter saves the
    # caller a second `ls-remote`/`for-each-ref` snapshot either side of the run.
    _push_branch(repo, "feat", land_in_main=True)
    monkeypatch.setattr(bs.git, "toplevel", lambda _root: repo)
    _merged_at_tip(monkeypatch, repo, "feat")

    result = bs.BranchSweepResult()
    assert bs.run_branch_sweep_recipe(_cfg(repo), [], result=result) == 0

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")


def test_recipe_result_records_an_unavailable_remote(repo: Path, monkeypatch) -> None:
    # A failed sweep exits 2; the caller still gets the reason on the object it
    # passed in rather than having to re-read stderr.
    monkeypatch.setattr(bs.git, "toplevel", lambda _root: repo)

    def _sweep(_cfg, _root, *, echo, result=None):
        result.remote_unavailable = "remote unreachable"
        return result

    monkeypatch.setattr(bs, "sweep_branches", _sweep)

    result = bs.BranchSweepResult()
    assert bs.run_branch_sweep_recipe(_cfg(repo), [], result=result) == 2
    assert result.remote_unavailable == "remote unreachable"


def test_gh_unavailable_no_deletes(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _push_branch(repo, "other")

    def _boom(branch: str, state: str) -> list[dict[str, object]]:
        raise bs.GhError("`gh` not found on PATH")

    monkeypatch.setattr(bs, "prs_for_head", _boom)

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

    monkeypatch.setattr(bs, "prs_for_head", fake_prs)

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
    _fake_gh(monkeypatch, {"remote-only": _tip(other, "remote-only")})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.remote_deleted == ["remote-only"]
    assert not _branch_exists_remote(repo, "remote-only")
    archived = _git(repo, "ls-remote", "--tags", "origin", "refs/tags/retired/remote-only")
    assert archived.stdout.split()[0] == _tip(other, "remote-only")


def _verdict(repo: Path, tip: str, merged_head: str) -> bs.MergedPrVerdict:
    return bs.merged_pr_verdict(
        repo,
        tip,
        [("7", merged_head)],
        landed_refs=["main"],
        remote="origin",
        coga_prefix="coga",
    )


def test_verdict_exact_merged_tip_lands(repo: Path) -> None:
    _push_branch(repo, "feat")
    verdict = _verdict(repo, _tip(repo, "feat"), _tip(repo, "feat"))
    assert verdict.landed is True
    assert "PR #7" in verdict.reason


def test_open_pr_refusal_is_noted_and_costs_no_git_comparison(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    _fake_gh(monkeypatch, {"feat": "0" * 40}, open_heads=frozenset({"feat"}))
    monkeypatch.setattr(
        bs,
        "merged_pr_verdict",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no comparison")),
    )

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert any("'feat' has an open PR" in note for note in result.notes), result.notes


def test_no_pr_branch_costs_one_gh_call(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    calls: list[tuple[str, str]] = []

    def fake_prs(branch: str, state: str) -> list[dict[str, object]]:
        calls.append((branch, state))
        return []

    monkeypatch.setattr(bs, "prs_for_head", fake_prs)

    bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert calls == [("feat", "merged")]


# --- the squash-merge shapes Coga itself produces ---------------------------


def test_tip_moved_by_sync_commits_is_deleted(repo: Path, monkeypatch) -> None:
    # PR squash-merged, then the still-checked-out branch kept receiving Coga
    # state commits — including a clean `Merge main state into feat` — so the
    # tip is neither the merged head nor an ancestor of main.
    _push_branch(repo, "feat")
    merged_head = _tip(repo, "feat")
    _squash_merge(repo, "feat")
    _state_commit(repo, "feat", "one")
    _git(repo, "merge", "--no-ff", "--no-edit", "-m", "Merge main state into feat", "main")
    _state_commit(repo, "feat", "two")
    _git(repo, "checkout", "main")
    assert _tip(repo, "feat") != merged_head
    assert _git(repo, "merge-base", "--is-ancestor", "feat", "main", check=False).returncode != 0
    _fake_gh(monkeypatch, {"feat": merged_head})
    tip = _tip(repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]
    assert result.skipped == []
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")
    assert _tip(repo, "refs/tags/retired/feat") == tip


def test_remote_ref_that_moved_past_merged_head_is_kept(
    repo: Path, monkeypatch
) -> None:
    # The widened rule is for the local ref only: even when the remote tip's
    # objects are local (they were pushed from here), `origin/feat` is
    # released only at the exact merged tip.
    _push_branch(repo, "feat")
    merged_head = _tip(repo, "feat")
    _squash_merge(repo, "feat")
    _state_commit(repo, "feat", "one")
    _git(repo, "push", "origin", "feat")
    _git(repo, "checkout", "main")
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == []
    assert _branch_exists_remote(repo, "feat")
    assert any("skipping remote origin/feat" in note for note in result.notes)


def test_control_merged_from_stale_local_main_is_not_unmerged_work(
    repo: Path, monkeypatch
) -> None:
    # The branch merged `origin/main` after its PR landed, and local `main`
    # lags: main's own source commits are landed work, not the ref's.
    _push_branch(repo, "feat")
    merged_head = _tip(repo, "feat")
    _squash_merge(repo, "feat")
    _commit(repo, "later.txt", "main moved on", "main change")
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "feat")
    _git(repo, "merge", "--no-ff", "--no-edit", "-m", "Merge main state into feat", "origin/main")
    _git(repo, "checkout", "main")
    _git(repo, "reset", "--hard", "HEAD~1")
    assert _tip(repo, "main") != _tip(repo, "origin/main")
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]


def test_tip_moved_by_real_changes_is_skipped(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    merged_head = _tip(repo, "feat")
    _squash_merge(repo, "feat")
    _state_commit(repo, "feat", "one")
    _git(repo, "checkout", "feat")
    (repo / "src").mkdir()
    _commit(repo, "src/thing.py", "unpushed work", "real follow-up")
    _git(repo, "checkout", "main")
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert any(
        "PR #7" in note and "src/thing.py" in note for note in result.notes
    ), result.notes
    assert any("no merged PR vouching for it" in note for note in result.notes)


def _merge_rebased_copy(
    repo: Path, branch: str, *, amend: str | None = None, squash: bool = True,
) -> str:
    """Rebase `branch` onto a newer main elsewhere, push that copy, and merge it.

    The local ref keeps its pre-rebase commits, the shape a review follow-up
    pushed from a scratch clone leaves behind. `amend` changes the copied
    patch the way a conflict resolution would. Returns the merged head.
    """
    _commit(repo, "later.txt", "main moved on", "main change")
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "-b", "copy", "main")
    _git(repo, "cherry-pick", branch)
    if amend is not None:
        (repo / f"{branch}.txt").write_text(amend)
        _git(repo, "commit", "--amend", "--no-edit", "-a")
    _git(repo, "push", "--force", "origin", f"copy:{branch}")
    merged_head = _tip(repo, "copy")
    _git(repo, "checkout", "main")
    _git(repo, "branch", "-D", "copy")
    if squash:
        _squash_merge(repo, f"origin/{branch}")
    else:
        _git(repo, "merge", "--no-ff", "--no-edit", f"origin/{branch}")
        _git(repo, "push", "origin", "main")
    assert _git(repo, "merge-base", "--is-ancestor", branch, merged_head, check=False).returncode != 0
    return merged_head


@pytest.mark.parametrize("squash", [False, True])
def test_local_ref_rebased_elsewhere_then_merged_is_deleted(
    repo: Path, monkeypatch, squash: bool,
) -> None:
    # The local commits are patch-equivalent to the merged head's rebased
    # copies, so the merged PR vouches for them even though no ancestry does.
    _push_branch(repo, "feat")
    tip = _tip(repo, "feat")
    merged_head = _merge_rebased_copy(repo, "feat", squash=squash)
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")
    assert _tip(repo, "refs/tags/retired/feat") == tip
    assert any("refs/pull/7/head" in note for note in result.notes), result.notes


def test_local_ref_whose_rebase_changed_the_patch_is_kept(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    merged_head = _merge_rebased_copy(repo, "feat", amend="resolved differently")
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert any("PR #7" in note and "feat.txt" in note for note in result.notes), result.notes


@pytest.mark.parametrize("squash", [False, True])
@pytest.mark.parametrize("change", ["indentation", "line-endings"])
def test_local_ref_whose_rebase_changed_whitespace_is_kept(
    repo: Path, monkeypatch, squash: bool, change: str,
) -> None:
    original = "def f(x):\n    if x:\n        print(x)\n    return 1\n"
    changed = (
        original.replace("    return", "        return")
        if change == "indentation" else original.replace("\n", "\r\n")
    )
    _push_branch(repo, "feat")
    _git(repo, "checkout", "feat")
    (repo / "feat.txt").write_text(original)
    _git(repo, "commit", "--amend", "--no-edit", "-a")
    _git(repo, "checkout", "main")
    merged_head = _merge_rebased_copy(repo, "feat", amend=changed, squash=squash)
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert any("feat.txt" in note for note in result.notes), result.notes


def test_patch_comparison_failure_preserves_rebased_branch(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    merged_head = _merge_rebased_copy(repo, "feat")
    _fake_gh(monkeypatch, {"feat": merged_head})
    run = subprocess.run

    def fail_patch_id(argv, **kwargs):
        if "patch-id" in argv:
            return subprocess.CompletedProcess(argv, 1, b"", b"patch-id unavailable")
        return run(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_patch_id)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert any("patches could not be compared" in note for note in result.notes)


def test_reapplied_local_source_needs_another_merged_patch_match(repo: Path) -> None:
    _git(repo, "checkout", "-b", "feat")
    _commit(repo, "base.txt", "changed", "feature")
    original = _tip(repo, "feat")
    _git(repo, "checkout", "main")
    _commit(repo, "later.txt", "main advanced", "main change")
    _git(repo, "checkout", "-b", "copy")
    _git(repo, "cherry-pick", original)
    _git(repo, "revert", "--no-edit", "HEAD")
    merged_head = _tip(repo, "copy")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--ff-only", "copy")
    _git(repo, "checkout", "feat")
    _git(repo, "revert", "--no-edit", "HEAD")
    _commit(repo, "base.txt", "changed", "reapply local work")

    verdict = _verdict(repo, _tip(repo, "feat"), merged_head)

    assert verdict.landed is False
    assert "base.txt" in verdict.reason


@pytest.mark.parametrize("submodule_format", ["log", "diff"])
def test_submodule_display_config_cannot_hide_a_changed_gitlink(
    repo: Path, submodule_format: str,
) -> None:
    # Gitlink objects need not be checked out. Use distinct valid commit IDs.
    first = _tip(repo, "main")
    _commit(repo, "later.txt", "one", "next gitlink target")
    second = _tip(repo, "main")
    _commit(repo, "later.txt", "two", "another gitlink target")
    third = _tip(repo, "main")
    _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{first},a-sub")
    _git(repo, "commit", "-m", "add gitlink")
    _git(repo, "checkout", "-b", "feat")
    _git(repo, "update-index", "--cacheinfo", f"160000,{second},a-sub")
    _commit(repo, "base.txt", "feature", "local source and gitlink")
    tip = _tip(repo, "feat")
    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "copy")
    _git(repo, "update-index", "--cacheinfo", f"160000,{third},a-sub")
    _commit(repo, "base.txt", "feature", "different gitlink with same source")
    merged_head = _tip(repo, "copy")
    _git(repo, "config", "diff.submodule", submodule_format)

    verdict = _verdict(repo, tip, merged_head)

    assert verdict.landed is False
    assert "a-sub" in verdict.reason


@pytest.mark.parametrize("unpushed_source", [False, True])
def test_daily_autoclose_sweeps_unclaimed_branches(
    repo: Path, monkeypatch, capsys, unpushed_source: bool,
) -> None:
    """Exercise the daily script and real recipes against a local bare origin."""
    _push_branch(repo, "feat")
    merged_head = _tip(repo, "feat")
    _squash_merge(repo, "feat")
    _state_commit(repo, "feat", "one")
    if unpushed_source:
        _commit(repo, "feat.txt", "unpushed source change", "follow-up")
    _git(repo, "checkout", "main")
    _fake_gh(monkeypatch, {"feat": merged_head})
    cfg = _cfg(repo)
    monkeypatch.setattr("coga.config.load_config", lambda: cfg)
    monkeypatch.setenv("COGA_TASK_SLUG", "recurring/autoclose-merged")
    run = subprocess.run
    bumps = []

    def run_with_bump(argv, **kwargs):
        if argv[1:4] == ["-m", "coga.cli", "bump"]:
            bumps.append(argv[4])
            return subprocess.CompletedProcess(argv, 0)
        return run(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", run_with_bump)
    script = (
        Path(__file__).resolve().parents[1]
        / "src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py"
    )
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(script))

    assert exc.value.code == 0
    assert bumps == ["recurring/autoclose-merged"]
    assert _branch_exists_local(repo, "feat") is unpushed_source
    assert _branch_exists_remote(repo, "feat") is unpushed_source
    output = capsys.readouterr().out
    assert "no tickets bumped" in output
    assert "Branch Sweep" in output
    if unpushed_source:
        assert "feat.txt" in output


def test_evil_merge_of_control_state_keeps_branch(repo: Path, monkeypatch) -> None:
    # A merge commit is bookkeeping only when its result matches a parent for
    # every path; a conflict resolved in a source file is work.
    _push_branch(repo, "feat")
    merged_head = _tip(repo, "feat")
    _squash_merge(repo, "feat")
    _commit(repo, "base.txt", "main moved", "main change")
    _git(repo, "checkout", "feat")
    _git(repo, "merge", "--no-ff", "--no-edit", "-m", "Merge main state into feat", "main")
    (repo / "base.txt").write_text("resolved differently")
    _git(repo, "commit", "-a", "--amend", "--no-edit")
    _git(repo, "checkout", "main")
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.skipped == ["feat"]
    assert any("base.txt" in note for note in result.notes), result.notes


def _push_fix_from_elsewhere(repo: Path, tmp_path: Path, branch: str) -> str:
    """Push one more commit to `branch` from another clone; return its SHA."""
    other = tmp_path / "other"
    subprocess.run(
        ["git", "clone", "-q", _remote_url(repo), str(other)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(other, "config", "user.email", "t@example.com")
    _git(other, "config", "user.name", "Tester")
    _git(other, "checkout", branch)
    _commit(other, "review-fix.txt", "fix", "review fix")
    _git(other, "push", "origin", branch)
    return _tip(other, branch)


def test_merged_head_absent_from_local_graph_is_fetched_and_deleted(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    # The dominant backlog shape: the local ref lags the merged head because
    # the last commit was pushed from another checkout, and retire already
    # deleted the remote branch. GitHub still serves `refs/pull/<n>/head`.
    _push_branch(repo, "feat")
    merged_head = _push_fix_from_elsewhere(repo, tmp_path, "feat")
    _git(repo, "push", "origin", "--delete", "feat")
    origin = tmp_path / "origin.git"
    _git(origin, "update-ref", "refs/pull/7/head", merged_head)
    assert _git(repo, "cat-file", "-e", merged_head, check=False).returncode != 0
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert not _branch_exists_local(repo, "feat")
    assert _git(repo, "cat-file", "-e", merged_head, check=False).returncode == 0
    # Fetched as objects only: no ref was written for it.
    assert "refs/pull" not in _git(repo, "for-each-ref").stdout


def test_merged_head_that_cannot_be_fetched_keeps_branch(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    merged_head = _push_fix_from_elsewhere(repo, tmp_path, "feat")
    _git(repo, "push", "origin", "--delete", "feat")
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert any("could not be fetched" in note for note in result.notes), result.notes


def test_diverged_lineage_with_local_work_is_skipped(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    # Neither ref contains the other and the local side holds source work:
    # a merged PR alone must never force-delete it.
    _push_branch(repo, "feat")
    merged_head = _push_fix_from_elsewhere(repo, tmp_path, "feat")
    origin = tmp_path / "origin.git"
    _git(origin, "update-ref", "refs/pull/7/head", merged_head)
    _git(repo, "checkout", "feat")
    _commit(repo, "local-only.txt", "never pushed", "local work")
    _git(repo, "checkout", "main")
    _fake_gh(monkeypatch, {"feat": merged_head})

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert any("local-only.txt" in note for note in result.notes), result.notes


# --- the run record ----------------------------------------------------------


def _host_task(repo: Path) -> Path:
    task_dir = repo / "coga" / "tasks" / "recurring" / "branch-sweep"
    task_dir.mkdir(parents=True)
    host = task_dir / "ticket.md"
    host.write_text(
        _ticket_text("branch-sweep", status="draft", body="", blackboard="")
    )
    return host


def test_recipe_writes_report_to_task_blackboard(
    repo: Path, monkeypatch, capsys
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    _push_branch(repo, "kept")
    host = _host_task(repo)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    monkeypatch.setenv("COGA_TASK_SLUG", "recurring/branch-sweep")
    monkeypatch.setattr(bs.git, "toplevel", lambda _root: repo)
    _merged_at_tip(monkeypatch, repo, "feat")

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 0

    text = host.read_text()
    report = text.split("<!-- coga:blackboard -->", 1)[1]
    assert bs.SWEEP_REPORT_HEADING in report
    assert "Task: `recurring/branch-sweep`" in report
    assert "- deleted local: feat" in report
    assert "- deleted remote: feat" in report
    assert "- skipped: kept" in report
    assert "'kept' has unmerged work and no merged PR vouching for it" in report
    assert bs.SWEEP_REPORT_HEADING not in capsys.readouterr().out


def test_recipe_writes_report_to_stdout_without_a_task(
    repo: Path, monkeypatch, capsys
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    monkeypatch.setattr(bs.git, "toplevel", lambda _root: repo)
    _merged_at_tip(monkeypatch, repo, "feat")

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 0

    out = capsys.readouterr().out
    assert bs.SWEEP_REPORT_HEADING in out
    assert "- deleted local: feat" in out


@pytest.mark.parametrize(
    ("failure_field", "result_text"),
    [
        ("remote_unavailable", "partial sweep"),
        ("gh_unavailable", "partial sweep"),
        ("worktree_unavailable", "the sweep stopped early"),
        ("state_root_unavailable", "the sweep stopped early"),
    ],
)
def test_recipe_records_a_failed_sweep_on_the_blackboard(
    repo: Path, monkeypatch, failure_field: str, result_text: str
) -> None:
    host = _host_task(repo)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    monkeypatch.setattr(bs.git, "toplevel", lambda _root: repo)

    def _sweep(_cfg, _root, *, echo, result=None):
        setattr(result, failure_field, "probe unavailable")
        return result

    monkeypatch.setattr(bs, "sweep_branches", _sweep)

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 2
    assert f"Result: {result_text} — probe unavailable" in host.read_text()
    assert "Counts: 0 local and 0 remote branch(es) deleted" in host.read_text()


def test_recipe_reports_local_cleanup_when_remote_listing_fails(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat", land_in_main=True)
    host = _host_task(repo)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    monkeypatch.setattr(bs.git, "toplevel", lambda _root: repo)
    _merged_at_tip(monkeypatch, repo, "feat")
    real_git = bs._git

    def fail_remote_listing(
        root: Path, *args: str, input: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("ls-remote", "--heads"):
            return subprocess.CompletedProcess(
                args, 1, stdout="", stderr="simulated remote listing failure"
            )
        return real_git(root, *args, input=input)

    monkeypatch.setattr(bs, "_git", fail_remote_listing)

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 2

    report = host.read_text()
    assert "Result: partial sweep — simulated remote listing failure" in report
    assert "Counts: 1 local and 0 remote branch(es) deleted" in report
    assert "- deleted local: feat" in report
    assert "stopped early" not in report
    assert not _branch_exists_local(repo, "feat")
    assert _git(repo, "ls-remote", "--heads", "origin", "feat").stdout.strip()


@pytest.mark.parametrize("open_pr", [False, True])
def test_gc_preserves_checkout_with_new_local_work(
    repo: Path, tmp_path: Path, monkeypatch, open_pr: bool,
) -> None:
    _push_branch(repo, "reuse")
    merged = _tip(repo, "reuse")
    worktree = tmp_path / "new-work"
    _git(repo, "worktree", "add", str(worktree), "reuse")
    _commit(worktree, "new.txt", "not merged", "new source work")
    _own_worktrees(repo)
    _fake_gh(monkeypatch, {"reuse": merged},
             open_heads=frozenset({"reuse"}) if open_pr else frozenset())

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert worktree.is_dir()
    assert (worktree / "new.txt").read_text() == "not merged"
    assert _branch_exists_local(repo, "reuse")
    assert _git(repo, "ls-remote", "--heads", "origin", "reuse").stdout.strip()
    assert not result.worktree_removed


@pytest.mark.parametrize("has_merged_pr", [False, True])
def test_gc_preserves_landed_checkout_with_open_pr(
    repo: Path, tmp_path: Path, monkeypatch, has_merged_pr: bool,
) -> None:
    _push_branch(repo, "reuse", land_in_main=True)
    worktree = tmp_path / "open-pr"
    _git(repo, "worktree", "add", str(worktree), "reuse")
    _own_worktrees(repo)
    _fake_gh(monkeypatch,
             {"reuse": _tip(repo, "reuse")} if has_merged_pr else {},
             open_heads=frozenset({"reuse"}))

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert worktree.is_dir()
    assert _branch_exists_local(repo, "reuse")
    assert result.worktree_pinned == ["reuse"]
    assert not result.local_deleted and not result.remote_deleted


# --- Terminal owners: closed unmerged PRs -----------------------------------


def _closed_at_tip(monkeypatch, repo: Path, *branches: str, **kwargs) -> None:
    """Stub gh so each branch's current tip is the head of a closed, unmerged PR."""
    _fake_gh(
        monkeypatch,
        closed={branch: _tip(repo, branch) for branch in branches},
        **kwargs,
    )


def _write_owner(repo: Path, slug: str, *, status: str, branches: list[str]) -> None:
    task_dir = repo / "coga" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"branch: {branch}" for branch in branches)
    (task_dir / f"{slug}.md").write_text(
        _ticket_text(slug, status=status, body="", blackboard=f"## Dev\n{lines}")
    )


@pytest.mark.parametrize("status", ["done", "canceled"])
def test_closed_unmerged_pr_releases_branch_of_terminal_owner(
    repo: Path, monkeypatch, status: str
) -> None:
    _push_branch(repo, "feat")
    tip = _tip(repo, "feat")
    _write_owner(repo, "abandoned", status=status, branches=["feat"])
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == ["feat"]
    assert result.failure is None
    assert _remote_tag(repo, "retired/feat") == tip
    assert any(
        f"owned by terminal ticket(s) abandoned ({status})" in note
        and "#9" in note
        for note in result.notes
    )


def test_closed_unmerged_pr_without_an_owner_is_kept(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_incidental_mention_on_a_terminal_ticket_is_not_ownership(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    (repo / "coga" / "tasks").mkdir(parents=True)
    (repo / "coga" / "tasks" / "mentions.md").write_text(
        _ticket_text(
            "mentions",
            status="done",
            body="See the abandoned feat branch for an earlier attempt.",
            blackboard="## Notes\nfeat was closed unmerged.",
        )
    )
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_closed_pr_branch_of_an_active_owner_is_kept(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "still-going", status="in_progress", branches=["feat"])
    monkeypatch.setattr(bs, "prs_for_head", _gh_must_not_be_consulted)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")


def test_closed_pr_branch_shared_with_a_live_ticket_is_kept(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="canceled", branches=["feat"])
    _write_owner(repo, "picked-up", status="active", branches=["feat"])
    monkeypatch.setattr(bs, "prs_for_head", _gh_must_not_be_consulted)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == []
    assert any("recorded on a live ticket" in note for note in result.notes)


def test_closed_pr_branch_claimed_in_another_workspace_is_kept(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="done", branches=["feat"])
    _closed_at_tip(monkeypatch, repo, "feat")
    monkeypatch.setattr(
        bs,
        "live_checkout_claim",
        lambda *_a, **_k: "live ticket 'other:resumed' also records branch 'feat'",
    )

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert any("other:resumed" in note for note in result.notes)


def test_closed_pr_branch_with_an_open_pr_is_kept(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="done", branches=["feat"])
    _closed_at_tip(monkeypatch, repo, "feat", open_heads=frozenset({"feat"}))

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_source_commit_after_pr_closed_is_reported_and_kept(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="done", branches=["feat"])
    _closed_at_tip(monkeypatch, repo, "feat")
    _git(repo, "checkout", "feat")
    _commit(repo, "late.py", "print('unreviewed')\n", "work after the PR closed")
    _git(repo, "checkout", "main")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")
    assert any(
        "closed unmerged PR #9" in note and "late.py" in note
        for note in result.notes
    )


def test_state_commit_after_pr_closed_still_releases_branch(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    _closed_at_tip(monkeypatch, repo, "feat")
    _state_commit(repo, "feat", "bookkeeping")
    local_tip = _tip(repo, "feat")
    _git(repo, "checkout", "main")
    _write_owner(repo, "abandoned", status="done", branches=["feat"])

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == ["feat"]
    assert _remote_tag(repo, "retired/feat") == local_tip


def test_remote_moved_past_closed_head_keeps_the_remote_ref(
    repo: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="done", branches=["feat"])
    _closed_at_tip(monkeypatch, repo, "feat")
    other = repo.parent / "other"
    _git(repo.parent, "clone", "-q", "-b", "feat", _remote_url(repo), str(other))
    _git(other, "config", "user.email", "t@example.com")
    _git(other, "config", "user.name", "Tester")
    _commit(other, "pushed.py", "x = 1\n", "pushed from another clone")
    _git(other, "push", "origin", "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == []
    assert _branch_exists_remote(repo, "feat")
    assert any("not the head of its merged or closed PR" in note for note in result.notes)


def test_every_owned_branch_is_released(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "first")
    _push_branch(repo, "second")
    _write_owner(repo, "split-work", status="canceled", branches=["first", "second"])
    _closed_at_tip(monkeypatch, repo, "first", "second")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert sorted(result.local_deleted) == sorted(result.remote_deleted) == [
        "first",
        "second",
    ]


def test_owned_branch_with_no_pr_is_kept_for_a_human(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="canceled", branches=["feat"])
    _fake_gh(monkeypatch)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert any("no merged or closed PR vouches" in note for note in result.notes)


def test_closed_pr_archive_failure_keeps_both_refs(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="done", branches=["feat"])
    _closed_at_tip(monkeypatch, repo, "feat")
    real_git = bs._git

    def fail_tag_push(root: Path, *args: str, input: str | None = None):
        if args[0] == "push" and any("refs/tags/retired/feat" in arg for arg in args):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="tag push rejected")
        return real_git(root, *args, input=input)

    monkeypatch.setattr(bs, "_git", fail_tag_push)

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.failure is not None and "tag push rejected" in result.failure
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_closed_pr_branch_checked_out_is_kept(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="done", branches=["feat"])
    _closed_at_tip(monkeypatch, repo, "feat")
    _git(repo, "checkout", "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == []
    assert any("is the checked-out branch" in note for note in result.notes)


def test_closed_pr_branch_in_a_worktree_is_pinned(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "abandoned", status="done", branches=["feat"])
    _closed_at_tip(monkeypatch, repo, "feat")
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", str(linked), "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.worktree_pinned == ["feat"]
    assert linked.is_dir()
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def _write_worklist(repo: Path, *entries) -> None:
    from coga.retire_worklist import RETIRE_WORKLIST_HEADER, render_worklist

    path = repo / "coga" / "recurring" / "autoclose-merged" / "retires.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_worklist(RETIRE_WORKLIST_HEADER, entries))


def test_worklist_entry_owns_branch_after_its_ticket_is_deleted(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    from coga.retire_worklist import RetireFollowUp

    _push_branch(repo, "feat")
    _write_worklist(
        repo,
        RetireFollowUp("gone-ticket", "feat", str(tmp_path / "wiped"), "2026-10-01"),
    )
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == result.remote_deleted == ["feat"]
    assert any("gone-ticket (retires.md)" in note for note in result.notes)


def test_worklist_entry_for_another_clones_branch_is_not_ownership(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    from coga.retire_worklist import RetireFollowUp

    _push_branch(repo, "feat")
    foreign = tmp_path / "foreign"
    subprocess.run(["git", "init", "-q", "-b", "main", str(foreign)], check=True)
    _write_worklist(
        repo,
        RetireFollowUp(
            "foreign-ticket", "feat", str(foreign), "2026-10-01", owner=str(foreign)
        ),
    )
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.skipped == ["feat"]
    assert _branch_exists_local(repo, "feat")


def test_only_restricts_the_sweep_to_named_branches(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "mine")
    _push_branch(repo, "theirs")
    _write_owner(repo, "abandoned", status="done", branches=["mine", "theirs"])
    _closed_at_tip(monkeypatch, repo, "mine", "theirs")

    result = bs.sweep_branches(
        _cfg(repo), repo, echo=lambda _m: None, only={"mine"}
    )

    assert result.local_deleted == ["mine"]
    assert _branch_exists_local(repo, "theirs")


def test_ticket_disposal_releases_every_owned_closed_pr_branch(
    repo: Path, monkeypatch
) -> None:
    from coga.checkout_disposal import dispose_checkout

    _push_branch(repo, "first")
    _push_branch(repo, "second")
    _write_owner(repo, "declined", status="done", branches=["first", "second"])
    _closed_at_tip(monkeypatch, repo, "first", "second")
    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda _url: "CLOSED")
    monkeypatch.setattr("coga.branchcleanup.prs_for_head", lambda _b, _s: [])

    disposal = dispose_checkout(
        _cfg(repo),
        repo,
        branch="first",
        worktree=None,
        pr_url="https://github.com/owner/repo/pull/9",
        echo=lambda _m: None,
        owned_branches=["first", "second"],
    )

    assert disposal.disposed
    for branch in ("first", "second"):
        assert not _branch_exists_local(repo, branch)
        assert not _branch_exists_remote(repo, branch)


def test_ticket_disposal_reports_an_owned_branch_it_kept(
    repo: Path, monkeypatch
) -> None:
    from coga.checkout_disposal import dispose_checkout

    _push_branch(repo, "first")
    _push_branch(repo, "second")
    _write_owner(repo, "declined", status="done", branches=["first", "second"])
    _closed_at_tip(monkeypatch, repo, "first")
    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda _url: "CLOSED")
    monkeypatch.setattr("coga.branchcleanup.prs_for_head", lambda _b, _s: [])

    disposal = dispose_checkout(
        _cfg(repo),
        repo,
        branch="first",
        worktree=None,
        pr_url="https://github.com/owner/repo/pull/9",
        echo=lambda _m: None,
        owned_branches=["first", "second"],
    )

    assert not disposal.disposed
    assert disposal.branches_remaining == ["second"]
    assert "'second'" in disposal.reason
    assert not _branch_exists_local(repo, "first")


def test_fenced_example_never_authorizes_closed_pr_deletion(repo: Path, monkeypatch) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "done", status="done", branches=["actual"])
    ticket = repo / "coga/tasks/done.md"
    ticket.write_text(ticket.read_text() + "\n```yaml\nbranch: feat\n```\n")
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _: None)

    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


@pytest.mark.parametrize("other_workspace", [False, True])
def test_live_secondary_branch_claim_preserves_closed_pr(
    repo: Path, monkeypatch, other_workspace: bool,
) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "done", status="done", branches=["feat"])
    workspace = repo / "service" if other_workspace else repo
    current = repo
    if other_workspace:
        current = repo / "alpha"
        current.mkdir()
        (repo / "coga").rename(current / "coga")
        (workspace / "coga").mkdir(parents=True)
        (workspace / "coga/coga.toml").write_text('version = 1\n')
    ticket = workspace / "coga/tasks/recurring/live/ticket.md"
    ticket.parent.mkdir(parents=True)
    ticket.write_text(_ticket_text(
        "live", status="in_progress", body="",
        blackboard="## Dev\nbranch: primary\nbranch: feat\n",
    ))
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(current), repo, echo=lambda _: None)

    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


@pytest.mark.parametrize("unreadable", [False, True])
def test_disposal_proves_secondary_merged_branch_unclaimed_across_workspaces(
    repo: Path, monkeypatch, unreadable: bool,
) -> None:
    from coga.checkout_disposal import dispose_checkout

    for branch in ("first", "second"):
        _push_branch(repo, branch)
    _write_owner(repo, "done", status="done", branches=["first", "second"])
    current = repo / "alpha"
    current.mkdir()
    (repo / "coga").rename(current / "coga")
    workspace = repo / "service"
    (workspace / "coga").mkdir(parents=True)
    (workspace / "coga/coga.toml").write_text('version = 1\n')
    _write_owner(workspace, "live", status="active", branches=["second"])
    if unreadable:
        (workspace / "coga/tasks/live.md").write_text("---\nbroken: [\n---\n")
    _fake_gh(monkeypatch, merged={b: _tip(repo, b) for b in ("first", "second")})
    monkeypatch.setattr("coga.branchcleanup.prs_for_head", lambda *_: [])

    disposal = dispose_checkout(
        _cfg(current), repo, branch="first", worktree=None, pr_url=None,
        owned_branches=["first", "second"], echo=lambda _: None,
    )

    assert not disposal.disposed
    assert _branch_exists_local(repo, "second")
    assert _branch_exists_remote(repo, "second")


def test_secondary_branch_debt_survives_ticket_deletion_and_retries(
    repo: Path, monkeypatch,
) -> None:
    from coga import autoclose as am
    from coga import retire_worklist as rw

    for branch in ("first", "second"):
        _push_branch(repo, branch)
    _write_owner(repo, "done", status="done", branches=["first", "second"])
    _write_worklist(repo, rw.RetireFollowUp("done", "first", "", "2026-10-01"))
    path = repo / "coga/recurring/autoclose-merged/retires.md"
    _closed_at_tip(monkeypatch, repo, "first")
    monkeypatch.setattr("coga.branchcleanup.prs_for_head", lambda *_: [])
    cfg = _cfg(repo)
    result = am.AutocloseResult()
    am._dispose_checkouts(cfg, result)
    assert result.checkouts[0].disposal.branches_remaining == ["second"]

    # Reconciliation must backfill an old single-branch entry before pruning.
    rw.reconcile_worklist(cfg, path, root=repo)
    (repo / "coga/tasks/done.md").unlink()
    change = rw.reconcile_worklist(cfg, path, root=repo)
    assert len(change.open) == 1
    assert "second" in change.open[0].branch_names

    # A later PR disposition is enough to drain even with the ticket gone.
    _closed_at_tip(monkeypatch, repo, "second")
    retried = am.AutocloseResult()
    am._dispose_checkouts(cfg, retried)
    assert retried.checkouts[0].disposed
    assert not _branch_exists_local(repo, "second")
    assert not _branch_exists_remote(repo, "second")
    assert rw.reconcile_worklist(cfg, path, root=repo).open == []


@pytest.mark.parametrize("skip_disposal", [False, True])
def test_autoclose_records_secondary_debt_even_when_disposal_is_skipped(
    repo: Path, monkeypatch, skip_disposal: bool,
) -> None:
    from coga import autoclose as am
    from coga import retire_worklist as rw

    for branch in ("first", "second"):
        _push_branch(repo, branch)
    _write_owner(repo, "done", status="done", branches=["first", "second"])
    template = repo / "coga/recurring/autoclose-merged"
    template.mkdir(parents=True)
    (template / "ticket.md").write_text("template\n")
    period = repo / "coga/tasks/recurring/autoclose-merged/ticket.md"
    period.parent.mkdir(parents=True)
    period.write_text(_ticket_text("period", status="in_progress", body="", blackboard=""))
    monkeypatch.setattr(am, "blackboard_from_env", lambda _: period)
    _closed_at_tip(monkeypatch, repo, "first")
    monkeypatch.setattr("coga.branchcleanup.prs_for_head", lambda *_: [])
    result = am.AutocloseResult(closed=[am.ClosedTicket(
        "done", "Done", branch="first", worktree=None, branches=("first", "second"),
    )])
    cfg = _cfg(repo)
    if skip_disposal:
        result.disposal_skipped = "off control"
    else:
        am._dispose_checkouts(cfg, result)

    assert am._report_retire_followups(cfg, result)
    path = template / "retires.md"
    [entry] = rw.parse_worklist(path.read_text())[1]
    assert entry.branch_names == ("first", "second")
    (repo / "coga/tasks/done.md").unlink()
    assert len(rw.reconcile_worklist(cfg, path, root=repo).open) == 1


@pytest.mark.parametrize("checkout", ["foreign-primary", "foreign-linked", "missing", "primary"])
def test_terminal_ticket_cannot_reintroduce_foreign_branch_authority(
    repo: Path, monkeypatch, checkout: str,
) -> None:
    from coga.retire_worklist import RetireFollowUp

    _push_branch(repo, "feat")
    _write_owner(repo, "done", status="done", branches=["feat"])
    recorded = repo
    if checkout.startswith("foreign"):
        owner = repo.parent / "foreign"
        _git(repo.parent, "clone", "-q", "-b", "feat", str(repo), str(owner))
        recorded = owner
        if checkout == "foreign-linked":
            recorded = repo.parent / "foreign-linked"
            _git(owner, "worktree", "add", "-b", "elsewhere", str(recorded))
        _write_worklist(repo, RetireFollowUp(
            "done", "feat", str(recorded), "2026-10-01", owner=str(owner),
        ))
    elif checkout == "missing":
        recorded = repo.parent / "unavailable"
    ticket = repo / "coga/tasks/done.md"
    ticket.write_text(ticket.read_text() + f"\nworktree: {recorded}\n")
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _: None)

    if checkout == "primary":
        assert result.local_deleted == result.remote_deleted == ["feat"]
    else:
        assert result.local_deleted == result.remote_deleted == []
        assert _branch_exists_local(repo, "feat")
        assert _branch_exists_remote(repo, "feat")
        assert any("grant no cleanup authority here" in note for note in result.notes)


@pytest.mark.parametrize("container", ["- ", "1. ", "> - ", "  - "])
def test_list_contained_fenced_example_is_not_branch_ownership(
    repo: Path, monkeypatch, container: str,
) -> None:
    _push_branch(repo, "feat")
    _write_owner(repo, "done", status="done", branches=["actual"])
    ticket = repo / "coga/tasks/done.md"
    ticket.write_text(ticket.read_text() + f"\n{container}```yaml\n  branch: feat\n  ```\n")
    _closed_at_tip(monkeypatch, repo, "feat")

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _: None)

    assert result.local_deleted == result.remote_deleted == []
    assert _branch_exists_local(repo, "feat")
    assert _branch_exists_remote(repo, "feat")


def test_disposal_retains_proven_owner_after_removing_recorded_worktree(
    repo: Path, monkeypatch,
) -> None:
    from coga.checkout_disposal import dispose_checkout

    _push_branch(repo, "first", land_in_main=True)
    _push_branch(repo, "second")
    linked = repo.parent / "linked"
    _git(repo, "worktree", "add", str(linked), "first")
    _write_owner(repo, "done", status="done", branches=["first", "second"])
    ticket = repo / "coga/tasks/done.md"
    ticket.write_text(ticket.read_text() + f"\nworktree: {linked}\n")
    _fake_gh(monkeypatch, merged={"first": _tip(repo, "first")}, closed={"second": _tip(repo, "second")})
    monkeypatch.setattr("coga.branchcleanup.prs_for_head", bs.prs_for_head)

    result = dispose_checkout(
        _cfg(repo), repo, branch="first", worktree=str(linked), pr_url=None,
        owned_branches=["first", "second"], echo=lambda _: None,
    )

    assert result.worktree_result.removed
    assert result.disposed
    assert not linked.exists()
    for branch in ("first", "second"):
        assert not _branch_exists_local(repo, branch)
        assert not _branch_exists_remote(repo, branch)
    assert _remote_tag(repo, "retired/second")
