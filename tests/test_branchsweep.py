from __future__ import annotations

import shutil
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
) -> None:
    """Stub `gh pr list --head`: `merged` maps a branch to its merged head SHA."""
    heads = merged or {}

    def fake_prs(branch: str, state: str) -> list[dict[str, object]]:
        if state == "merged" and branch in heads:
            return [{"number": 7, "headRefOid": heads[branch]}]
        if state == "open" and branch in open_heads:
            return [{"number": 8, "headRefOid": heads.get(branch, "")}]
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
    monkeypatch.setattr(bs.git, "_toplevel", lambda _root: repo)

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
    monkeypatch.setattr(bs.git, "_toplevel", lambda _root: repo)
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
    monkeypatch.setattr(bs.git, "_toplevel", lambda _root: repo)

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

    result = bs.sweep_branches(_cfg(repo), repo, echo=lambda _m: None)

    assert result.local_deleted == ["feat"]
    assert result.remote_deleted == ["feat"]
    assert result.skipped == []
    assert not _branch_exists_local(repo, "feat")
    assert not _branch_exists_remote(repo, "feat")


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
    monkeypatch.setattr(bs.git, "_toplevel", lambda _root: repo)
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
    monkeypatch.setattr(bs.git, "_toplevel", lambda _root: repo)
    _merged_at_tip(monkeypatch, repo, "feat")

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 0

    out = capsys.readouterr().out
    assert bs.SWEEP_REPORT_HEADING in out
    assert "- deleted local: feat" in out


def test_recipe_records_a_failed_sweep_on_the_blackboard(
    repo: Path, monkeypatch
) -> None:
    host = _host_task(repo)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    monkeypatch.setattr(bs.git, "_toplevel", lambda _root: repo)

    def _sweep(_cfg, _root, *, echo, result=None):
        result.remote_unavailable = "remote unreachable"
        return result

    monkeypatch.setattr(bs, "sweep_branches", _sweep)

    assert bs.run_branch_sweep_recipe(_cfg(repo), []) == 2
    assert "Result: the sweep stopped early — remote unreachable" in host.read_text()
