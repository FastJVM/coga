"""The autoclose sweep's checkout disposal phase, on the real-git harness.

`test_autoclose.py` covers the close itself on a non-git fixture, where the
disposal phase is skipped. These tests give the sweep a repository, a linked
worktree, and a bare `origin`, so the shared retire proofs
(`coga.checkout_disposal`) run for real.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from coga import autoclose as am
from coga import retire_worklist as rw
from coga.config import load_config
from coga.create import create_task
from coga.taskfile import read_blackboard, replace_blackboard
from coga.ticket import Ticket

from conftest import GitRepo

PR_URL = "https://github.com/o/r/pull/30"


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc.stdout.strip()


def _local_branch_exists(root: Path, branch: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "--quiet",
             f"refs/heads/{branch}"],
            capture_output=True,
        ).returncode
        == 0
    )


def _remote_branch_exists(root: Path, branch: str) -> bool:
    return bool(_git(root, "ls-remote", "--heads", "origin", branch))


def _landed_checkout(repo: GitRepo, tmp_path: Path, branch: str = "feature-x") -> Path:
    """A linked worktree on `branch`, pushed to origin and fast-forwarded into main."""
    worktree = tmp_path / f"wt-{branch}"
    _git(repo.root, "worktree", "add", str(worktree), "-b", branch)
    _git(worktree, "config", "user.email", "t@example.com")
    _git(worktree, "config", "user.name", "Tester")
    (worktree / f"{branch}.txt").write_text("work\n")
    _git(worktree, "add", f"{branch}.txt")
    _git(worktree, "commit", "-m", f"{branch} work")
    _git(worktree, "push", "-u", "origin", branch)
    _git(repo.root, "merge", "--ff-only", branch)
    _git(repo.root, "push", "origin", "main")
    return worktree


def _final_step_ticket(
    repo: GitRepo, *, branch: str, worktree: Path, pr_url: str = PR_URL
) -> tuple[str, Path]:
    """An in-progress ticket on its final step whose `## Dev` names the checkout."""
    cfg = load_config(repo.coga_os)
    ref = create_task(
        cfg=cfg,
        title="Work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ticket = ref["path"]
    t = Ticket.read(ticket)
    steps = t.workflow["steps"]
    t.frontmatter["step"] = f"{len(steps)} ({steps[-1]['name']})"
    t.write(ticket)
    blackboard = read_blackboard(ticket, blackboard_required=False).rstrip()
    replace_blackboard(
        ticket,
        blackboard
        + f"\n\n## Dev\n\nbranch: {branch}\nworktree: {worktree}\npr: {pr_url}\n",
    )
    return ref["slug"], ticket


def _stub_gh(
    monkeypatch: pytest.MonkeyPatch,
    repo: GitRepo,
    *,
    merged_by_head: dict[str, str] | None = None,
) -> None:
    """Stub every `gh` lookup the close and the disposal proofs make.

    The close reads `pr_state` through `autoclose`; the proofs read their own
    bindings in `branchcleanup`. A recorded `pr:` resolves to MERGED at the
    branch's current tip; `merged_by_head` maps a branch with no `pr:` to the
    head SHA of a merged PR found by head name.
    """
    heads = merged_by_head or {}

    def pr_head(url: str) -> tuple[str, str]:
        # Every ticket these tests record a `pr:` on is on `feature-x`.
        return "feature-x", _git(repo.root, "rev-parse", "refs/heads/feature-x")

    def prs_for_head(branch: str, state: str) -> list[dict[str, object]]:
        if state == "merged" and branch in heads:
            return [{"number": 5, "headRefOid": heads[branch]}]
        return []

    monkeypatch.setattr(am, "pr_state", lambda url: "MERGED")
    monkeypatch.setattr(am, "unanswered_review_threads", lambda url: [])
    monkeypatch.setattr("coga.branchcleanup.pr_state", lambda url: "MERGED")
    monkeypatch.setattr("coga.branchcleanup.pr_head", pr_head)
    monkeypatch.setattr("coga.branchcleanup.prs_for_head", prs_for_head)


def _capture_posts(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Every live Slack post as `(webhook url, text)`."""
    posts: list[tuple[str, str]] = []

    def fake(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        posts.append((url, json["text"]))

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", fake)
    return posts


IMPORTANT_WEBHOOK = "https://hooks.slack.com/services/important-test"


def _route_important(repo: GitRepo) -> None:
    toml = repo.coga_os / "coga.toml"
    toml.write_text(toml.read_text() + f'important_webhook = "{IMPORTANT_WEBHOOK}"\n')
    _git(repo.root, "commit", "-am", "route important")


def _period_task(repo: GitRepo, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Run the sweep as the `autoclose-merged` period task.

    Returns `(period ticket, template worklist)`.
    """
    template = repo.coga_os / "recurring" / "autoclose-merged"
    template.mkdir(parents=True)
    (template / "ticket.md").write_text("template\n")
    period = repo.coga_os / "tasks" / "recurring" / "autoclose-merged" / "ticket.md"
    period.parent.mkdir(parents=True)
    period.write_text(
        dedent(
            """
            ---
            title: Autoclose merged tickets
            status: in_progress
            owner: marc
            ---

            ## Description

            Period task.

            <!-- coga:blackboard -->
            """
        ).lstrip()
    )
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(period))
    monkeypatch.setenv("COGA_TASK_SLUG", "recurring/autoclose-merged")
    return period, template / rw.RETIRE_WORKLIST_FILENAME


def test_recipe_disposes_of_a_closed_tickets_landed_checkout(
    git_repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    worktree = _landed_checkout(git_repo, tmp_path)
    slug, ticket = _final_step_ticket(git_repo, branch="feature-x", worktree=worktree)
    _stub_gh(monkeypatch, git_repo)
    posts = _capture_posts(monkeypatch)
    result = am.AutocloseResult()

    assert am.run_autoclose_recipe(load_config(git_repo.coga_os), [], result=result) == 0

    assert Ticket.read(ticket).status == "done"
    # Worktree first (it pinned the branch), then local, then remote.
    assert not worktree.exists()
    assert not _local_branch_exists(git_repo.root, "feature-x")
    assert not _remote_branch_exists(git_repo.root, "feature-x")
    assert [item.slug for item in result.disposed] == [slug]
    assert result.retire_pending == []
    out = capsys.readouterr().out
    assert f"[autoclose] {slug}: Worktree cleanup: removed linked worktree" in out
    assert "1 checkout(s) disposed of" in out
    assert f"`coga retire {slug}`" not in out
    texts = [text for _url, text in posts]
    assert any(
        text.endswith(f"🧹 Autoclose disposed of 1 feature checkout (worktree and branch): `{slug}`")
        for text in texts
    )
    assert not any("⚠️" in text for text in texts)


def test_recipe_preserves_a_dirty_checkout_alerts_important_and_records_it(
    git_repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    worktree = _landed_checkout(git_repo, tmp_path)
    (worktree / "scratch.txt").write_text("unsaved\n")
    slug, ticket = _final_step_ticket(git_repo, branch="feature-x", worktree=worktree)
    _route_important(git_repo)
    period, worklist = _period_task(git_repo, monkeypatch)
    _stub_gh(monkeypatch, git_repo)
    posts = _capture_posts(monkeypatch)
    result = am.AutocloseResult()

    assert am.run_autoclose_recipe(load_config(git_repo.coga_os), [], result=result) == 0

    assert Ticket.read(ticket).status == "done"
    assert worktree.is_dir()
    assert _local_branch_exists(git_repo.root, "feature-x")
    assert _remote_branch_exists(git_repo.root, "feature-x")
    [preserved] = result.preserved
    assert preserved.slug == slug
    assert "contains tracked or untracked local state" in preserved.disposal.reason
    # A preserved closure is the one shape that still enters the worklist.
    _, entries = rw.parse_worklist(worklist.read_text())
    assert [(e.slug, e.branch, e.worktree) for e in entries] == [
        (slug, "feature-x", str(worktree))
    ]
    # The reason reaches coga-important — it is work a human must do.
    important = [text for url, text in posts if url == IMPORTANT_WEBHOOK]
    assert len(important) == 1
    assert "⚠️ 1 feature checkout needs a human" in important[0]
    assert f"`{slug}`" in important[0]
    assert "contains tracked or untracked local state" in important[0]
    assert not any("🧹" in text for _url, text in posts)
    report = period.read_text()
    assert "1 checkout(s) preserved" in report
    assert f"`coga retire {slug}`" in report
    assert "  - Worktree cleanup:" in report


def test_recipe_drains_a_worklist_entry_whose_ticket_is_gone(
    git_repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    # Retire preserved this checkout once and then deleted the ticket: the
    # entry has no ticket to read a `pr:` from, so the merge signal comes from
    # merged PRs by head name.
    worktree = _landed_checkout(git_repo, tmp_path, branch="orphan")
    template = git_repo.coga_os / "recurring" / "autoclose-merged"
    template.mkdir(parents=True)
    (template / "ticket.md").write_text("template\n")
    worklist = template / rw.RETIRE_WORKLIST_FILENAME
    worklist.write_text(
        rw.render_worklist(
            rw.RETIRE_WORKLIST_HEADER,
            [rw.RetireFollowUp("retired-long-ago", "orphan", str(worktree), "2026-09-01")],
        )
    )
    tip = _git(git_repo.root, "rev-parse", "refs/heads/orphan")
    _stub_gh(monkeypatch, git_repo, merged_by_head={"orphan": tip})
    _capture_posts(monkeypatch)
    result = am.AutocloseResult()

    # A hand run, not a period task: the backlog still drains.
    assert am.run_autoclose_recipe(load_config(git_repo.coga_os), [], result=result) == 0

    assert not worktree.exists()
    assert not _local_branch_exists(git_repo.root, "orphan")
    assert not _remote_branch_exists(git_repo.root, "orphan")
    [outcome] = result.checkouts
    assert outcome.slug == "retired-long-ago"
    assert outcome.title is None and not outcome.ticket_exists
    assert outcome.disposed
    _, entries = rw.parse_worklist(worklist.read_text())
    assert entries == []
    out = capsys.readouterr().out
    assert "`retired-long-ago` (worklist backlog, ticket already deleted)" in out
    assert f"retire worklist {worklist}: 0 open, 1 discharged (`retired-long-ago`)" in out


def test_entry_ticket_requires_an_exact_slug_match(
    git_repo: GitRepo, tmp_path: Path
) -> None:
    # The worklist names a deleted task whose slug is a unique prefix of a
    # newer one: CLI prefix resolution would report the old ticket as alive
    # and borrow the newer ticket's `pr:` for the disposal decision.
    worktree = _landed_checkout(git_repo, tmp_path, branch="foo-followup")
    cfg = load_config(git_repo.coga_os)
    slug, _ = _final_step_ticket(
        git_repo, branch="foo-followup", worktree=worktree, pr_url=PR_URL
    )
    stale = slug[: len(slug) // 2]
    assert stale != slug

    assert am._entry_ticket(cfg, stale) == (False, None)
    assert am._entry_ticket(cfg, slug) == (True, PR_URL)


def test_recipe_keeps_a_claimed_worklist_entry_with_its_reason(
    git_repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    worktree = _landed_checkout(git_repo, tmp_path)
    cfg = load_config(git_repo.coga_os)
    live = create_task(
        cfg=cfg, title="Still using it", workflow_name="code", contexts=[],
        owner="marc", agent="claude", status="active",
    )
    blackboard = read_blackboard(live["path"], blackboard_required=False).rstrip()
    replace_blackboard(live["path"], blackboard + "\n\n## Dev\n\nbranch: feature-x\n")
    template = git_repo.coga_os / "recurring" / "autoclose-merged"
    template.mkdir(parents=True)
    (template / "ticket.md").write_text("template\n")
    worklist = template / rw.RETIRE_WORKLIST_FILENAME
    worklist.write_text(
        rw.render_worklist(
            rw.RETIRE_WORKLIST_HEADER,
            [rw.RetireFollowUp("finished", "feature-x", str(worktree), "2026-09-01")],
        )
    )
    _stub_gh(monkeypatch, git_repo)
    _capture_posts(monkeypatch)
    result = am.AutocloseResult()

    assert am.run_autoclose_recipe(cfg, [], result=result) == 0

    assert worktree.is_dir()
    assert _local_branch_exists(git_repo.root, "feature-x")
    [outcome] = result.checkouts
    assert not outcome.disposed
    assert outcome.disposal.reason == (
        f"live ticket {live['slug']!r} also records branch 'feature-x'"
    )
    _, entries = rw.parse_worklist(worklist.read_text())
    assert [e.slug for e in entries] == ["finished"]
    out = capsys.readouterr().out
    assert "1 checkout(s) preserved" in out
    assert f"retire worklist {worklist}: 1 open" in out


def test_hand_run_off_the_control_branch_preserves_everything(
    git_repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    worktree = _landed_checkout(git_repo, tmp_path)
    slug, ticket = _final_step_ticket(git_repo, branch="feature-x", worktree=worktree)
    # The uncommitted ticket rides along: the close lands it on control through
    # the feature-branch plumbing path, exactly as a hand run off `main` would.
    _git(git_repo.root, "switch", "-c", "elsewhere")
    _stub_gh(monkeypatch, git_repo)
    posts = _capture_posts(monkeypatch)
    result = am.AutocloseResult()

    assert am.run_autoclose_recipe(load_config(git_repo.coga_os), [], result=result) == 0

    assert Ticket.read(ticket).status == "done"
    assert result.disposal_skipped == (
        "checkout is on 'elsewhere', not the control branch 'main'"
    )
    assert result.checkouts == []
    assert worktree.is_dir()
    assert _local_branch_exists(git_repo.root, "feature-x")
    assert _remote_branch_exists(git_repo.root, "feature-x")
    out = capsys.readouterr().out
    assert (
        "[autoclose] checkout disposal skipped (checkout is on 'elsewhere', not "
        "the control branch 'main') — every recorded checkout preserved." in out
    )
    assert f"`coga retire {slug}`" in out
    assert any(
        text.endswith(
            f"🧹 1 auto-closed ticket still has a feature checkout: `coga retire {slug}`"
        )
        for _url, text in posts
    )


@pytest.mark.parametrize("scan_raises", [False, True])
def test_branch_only_refusal_is_reported_and_recorded(
    git_repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    scan_raises: bool,
) -> None:
    worktree = _landed_checkout(git_repo, tmp_path)
    slug, ticket = _final_step_ticket(git_repo, branch="feature-x", worktree=worktree)
    blackboard = read_blackboard(ticket).replace(f"worktree: {worktree}\n", "")
    replace_blackboard(ticket, blackboard)
    _route_important(git_repo)
    _, worklist = _period_task(git_repo, monkeypatch)
    _stub_gh(monkeypatch, git_repo)
    posts = _capture_posts(monkeypatch)

    def refuse(*args, **kwargs):
        if scan_raises:
            raise OSError("claim scan unreadable")
        return "live ticket claims branch"

    monkeypatch.setattr("coga.checkout_disposal.live_checkout_claim", refuse)
    result = am.AutocloseResult()
    assert am.run_autoclose_recipe(load_config(git_repo.coga_os), [], result=result) == 0

    assert not result.disposed
    assert [item.slug for item in result.preserved] == [slug]
    assert [item.slug for item in result.retire_pending] == [slug]
    assert _local_branch_exists(git_repo.root, "feature-x")
    _, entries = rw.parse_worklist(worklist.read_text())
    assert [entry.slug for entry in entries] == [slug]
    assert any("⚠️" in text and slug in text for _, text in posts)


def test_disposal_from_recurring_control_checkout(
    git_repo: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from coga.checkout_disposal import dispose_checkout
    from coga.workspace_discovery import CONTROL_WORKTREE_OWNER_FILE

    worktree = _landed_checkout(git_repo, tmp_path)
    _stub_gh(monkeypatch, git_repo)
    parent = tmp_path / "coga-recurring-review"
    parent.mkdir()
    (parent / CONTROL_WORKTREE_OWNER_FILE).write_text("{}")
    control = parent / "checkout"
    _git(git_repo.root, "switch", "-c", "operator-work")
    _git(git_repo.root, "worktree", "add", str(control), "main")
    cfg = load_config(control / "coga", require_user=False)

    outcome = dispose_checkout(cfg, control, branch="feature-x",
                               worktree=str(worktree), pr_url=PR_URL)

    assert outcome.disposed
    assert not worktree.exists()
    assert not _local_branch_exists(control, "feature-x")
    assert not _remote_branch_exists(control, "feature-x")
