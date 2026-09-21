"""Tests for the deterministic push→PR→record recipe behind `coga open-pr`.

The recipe is the registered `open-pr` recipe in `coga.open_pr`; the seam that
resolves the task and gates the checkout is covered by
`test_open_pr_command.py`.

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
from coga.github_preflight import CheckResult, stranded_task_state_paths
from coga.git import sync_task_state
from coga.logfile import append_log
from coga.taskfile import read_blackboard
from coga.ticket import Ticket

from coga import git as coga_git
from coga.open_pr import (
    OpenPrError,
    _single_checkout_publishable_paths,
    open_pr,
    set_dev_pr,
)


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
    worktree: Path | str | None,
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


def test_open_pr_preserves_an_annotated_pr_line_that_already_matches(
    tmp_path, monkeypatch
):
    """An annotated `pr:` line naming this same PR survives the round trip.

    The post-write check compares `parse_pr_url(current_blackboard)` to the URL.
    While that parse rejected annotated lines it read `None != url`, so
    `set_dev_pr` rewrote the whole line and destroyed the annotation.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    url = "https://github.com/acme/repo/pull/21"
    _install_fake_gh(monkeypatch, bin_dir, create_url=url)

    wt = _feature_worktree(repo, tmp_path, "feature-annotated", commit=True)
    ticket = _write_ticket(
        repo.coga_os,
        "annotated",
        branch="feature-annotated",
        worktree=wt,
        pr=f"{url} (no CI configured on the repo)",
    )

    cfg = load_config(repo.coga_os)
    assert open_pr(cfg, slug="annotated", blackboard_path=ticket) == url

    blackboard = read_blackboard(ticket)
    assert f"pr: {url} (no CI configured on the repo)" in blackboard
    assert parse_pr_url(blackboard) == url


def test_open_pr_refuses_canceled_ticket_before_git_mutation(tmp_path) -> None:
    repo = init_git_repo(tmp_path)
    ticket_path = _write_ticket(
        repo.coga_os,
        "declined",
        branch="feature-x",
        worktree=tmp_path / "missing-worktree",
    )
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = "canceled"
    ticket.frontmatter.pop("step", None)
    ticket.write(ticket_path)

    with pytest.raises(OpenPrError, match="status 'canceled' is terminal"):
        open_pr(load_config(repo.coga_os), slug="declined", blackboard_path=ticket_path)


def _dirty_paths(repo) -> set[str]:
    return {
        line[3:]
        for line in repo.git(
            "status", "--porcelain", "--untracked-files=all"
        ).splitlines()
    }


def test_open_pr_commits_and_pushes_record_in_single_checkout(
    tmp_path, monkeypatch, real_git
):
    """The live ticket is on the feature branch in single-checkout mode.

    Recording the PR publishes the record to control only: the branch carries
    no Coga state commit, the live ticket and log stay dirty there by design,
    and a retry stays idempotent.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(
        monkeypatch,
        bin_dir,
        create_url="https://github.com/acme/repo/pull/12",
    )

    ticket = _write_ticket(
        repo.coga_os,
        "single-checkout-record",
        branch="single-checkout-record",
        worktree=repo.root,
    )
    repo.git("add", "--", "coga/tasks/single-checkout-record/ticket.md")
    repo.git("commit", "-m", "ticket: add single-checkout record")
    repo.git("push", "origin", "main")

    repo.checkout_branch("single-checkout-record")
    (repo.coga_os / "change.txt").write_text("a real change\n")
    repo.git("add", "--", "coga/change.txt")
    repo.git("commit", "-m", "feature: a real change")

    cfg = load_config(repo.coga_os)
    # A real supervised launch appends this before the agent invokes open-pr.
    # The single checkout must absorb that generated dirt without relaxing the
    # clean-tree refusal for any other path.
    append_log(cfg, "single-checkout-record", "human:marc", "launched")

    url = open_pr(
        cfg,
        slug="single-checkout-record",
        blackboard_path=ticket,
        single_checkout=True,
    )

    assert url == "https://github.com/acme/repo/pull/12"
    # Only Coga's live state is dirty; the branch itself carries no state commit.
    assert _dirty_paths(repo) == {
        "coga/tasks/single-checkout-record/ticket.md",
        "coga/log.md",
    }
    assert "Ticket: single-checkout-record — PR opened" not in repo.git(
        "log", "--format=%s"
    )
    assert repo.git(
        "diff", "--name-only", "origin/main...HEAD"
    ).split() == ["coga/change.txt"]
    # The generated `pr:` record and the launch audit line reached control.
    published_ticket = repo.git(
        "show",
        "refs/heads/main:coga/tasks/single-checkout-record/ticket.md",
        cwd=repo.origin,
    )
    assert "pr: https://github.com/acme/repo/pull/12" in published_ticket
    assert "[single-checkout-record] [human:marc] launched" in repo.git(
        "show", "refs/heads/main:coga/log.md", cwd=repo.origin
    )
    assert "coga/log.md" not in repo.git(
        "ls-tree", "-r", "--name-only", "refs/heads/single-checkout-record",
        cwd=repo.origin,
    ).split()


def test_open_pr_accepts_identical_generated_state_overlaps_from_preceding_bumps(
    tmp_path, monkeypatch, real_git
):
    """Preceding bumps publish task artifacts and companion tickets to control.

    None of it reaches the branch: it stays dirty in the single checkout, and
    open-pr's cleanliness gate leaves that live state alone.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(
        monkeypatch,
        bin_dir,
        create_url="https://github.com/acme/repo/pull/13",
    )

    ticket = _write_ticket(
        repo.coga_os,
        "post-bump",
        branch="post-bump",
        worktree=repo.root,
    )
    companion = _write_ticket(
        repo.coga_os,
        "post-bump-companion",
        branch="post-bump",
        worktree=repo.root,
    )
    repo.git(
        "add",
        "--",
        "coga/tasks/post-bump",
        "coga/tasks/post-bump-companion",
    )
    repo.git("commit", "-m", "ticket: add post-bump")
    repo.git("push", "origin", "main")

    repo.checkout_branch("post-bump")
    (repo.coga_os / "change.txt").write_text("a real change\n")
    repo.git("add", "--", "coga/change.txt")
    repo.git("commit", "-m", "feature: a real change")

    companion.write_text(
        companion.read_text().replace("step: 1 (open-pr)", "step: 2 (review)")
    )
    artifact = ticket.parent / "review.md"
    artifact.write_text("generated review artifact\n")
    ticket.write_text(
        ticket.read_text().replace("step: 1 (open-pr)", "step: 2 (open-pr)")
    )
    cfg = load_config(repo.coga_os)
    sync_task_state(
        cfg,
        companion.parent,
        message="Ticket: post-bump-companion — step 2 (review)",
    )
    sync_task_state(
        cfg,
        ticket.parent,
        message="Ticket: post-bump — step 2 (open-pr)",
    )

    url = open_pr(
        cfg,
        slug="post-bump",
        blackboard_path=ticket,
        single_checkout=True,
    )

    assert url == "https://github.com/acme/repo/pull/13"
    assert _dirty_paths(repo) == {
        "coga/tasks/post-bump/ticket.md",
        "coga/tasks/post-bump/review.md",
        "coga/tasks/post-bump-companion/ticket.md",
    }
    assert "pr: https://github.com/acme/repo/pull/13" in repo.git(
        "show", "refs/heads/main:coga/tasks/post-bump/ticket.md", cwd=repo.origin
    )
    assert repo.git(
        "show", "refs/heads/main:coga/tasks/post-bump/review.md", cwd=repo.origin
    ) == "generated review artifact\n"
    assert "coga/tasks/post-bump/review.md" not in repo.git(
        "ls-tree", "-r", "--name-only", "refs/heads/post-bump", cwd=repo.origin
    ).split()


def test_open_pr_rejects_single_checkout_with_only_generated_state(
    tmp_path, monkeypatch, real_git
):
    """Lifecycle commits do not count as an implementation to review."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    ticket = _write_ticket(
        repo.coga_os,
        "state-only-single-checkout",
        branch="state-only-single-checkout",
        worktree=repo.root,
    )
    repo.git("add", "--", "coga/tasks/state-only-single-checkout/ticket.md")
    repo.git("commit", "-m", "ticket: seed state-only task")
    repo.git("push", "origin", "main")

    repo.checkout_branch("state-only-single-checkout")
    ticket.write_text(
        ticket.read_text().replace("step: 1 (open-pr)", "step: 2 (open-pr)")
    )
    (repo.coga_os / "log.md").write_text("generated lifecycle state\n")
    cfg = load_config(repo.coga_os)
    sync_task_state(
        cfg,
        ticket.parent,
        message="Ticket: state-only-single-checkout — step 2 (open-pr)",
    )

    # The branch strands no lifecycle commit at all: it carried nothing but
    # generated state, so it adopted the control commit that accepted it.
    assert repo.git("rev-list", "--count", "main..HEAD").strip() == "0"
    with pytest.raises(OpenPrError, match="no commits ahead of"):
        open_pr(
            cfg,
            slug="state-only-single-checkout",
            blackboard_path=ticket,
            single_checkout=True,
        )

    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def test_open_pr_rejects_single_checkout_with_unreconciled_generated_state(
    tmp_path, monkeypatch, real_git
):
    """A commit that reconciliation could not remove is still not an implementation.

    Reconciliation fails closed, so a branch can legitimately keep a generated
    commit. The publishability classifier is the second line: a `merge=union`
    audit append is machine state whether or not the boundary reached it.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    ticket = _write_ticket(
        repo.coga_os,
        "unreconciled-single-checkout",
        branch="unreconciled-single-checkout",
        worktree=repo.root,
    )
    repo.git("add", "--", "coga/tasks/unreconciled-single-checkout/ticket.md")
    repo.git("commit", "-m", "ticket: seed unreconciled task")
    repo.git("push", "origin", "main")

    repo.checkout_branch("unreconciled-single-checkout")
    (repo.coga_os / "log.md").write_text("stranded audit line\n")
    repo.git("add", "--", "coga/log.md")
    repo.git("commit", "-m", "Log: stranded audit line on the branch")
    cfg = load_config(repo.coga_os)

    assert repo.git("rev-list", "--count", "main..HEAD").strip() == "1"
    with pytest.raises(OpenPrError, match="outside generated Coga task/log state"):
        open_pr(
            cfg,
            slug="unreconciled-single-checkout",
            blackboard_path=ticket,
            single_checkout=True,
        )

    assert not log.exists() or "pr create" not in log.read_text()


def test_open_pr_rejects_divergent_ticket_overlap_in_single_checkout(
    tmp_path, monkeypatch, real_git
):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    ticket = _write_ticket(
        repo.coga_os,
        "divergent-post-bump",
        branch="divergent-post-bump",
        worktree=repo.root,
    )
    repo.git("add", "--", "coga/tasks/divergent-post-bump/ticket.md")
    repo.git("commit", "-m", "ticket: add divergent post-bump")
    repo.git("push", "origin", "main")

    repo.checkout_branch("divergent-post-bump")
    (repo.coga_os / "change.txt").write_text("a real change\n")
    repo.git("add", "--", "coga/change.txt")
    repo.git("commit", "-m", "feature: a real change")
    ticket.write_text(
        ticket.read_text().replace("step: 1 (open-pr)", "step: 2 (open-pr)")
    )
    cfg = load_config(repo.coga_os)
    sync_task_state(
        cfg,
        ticket.parent,
        message="Ticket: divergent-post-bump — step 2 (open-pr)",
    )

    # Generated state no longer strands on the branch, so make the overlap the
    # real thing the gate is for: deliberate ticket prose committed here while
    # another process edits the same ticket on the control branch.
    ticket.write_text(ticket.read_text() + "\nbranch-authored prose\n")
    repo.git("add", "--", "coga/tasks/divergent-post-bump/ticket.md")
    repo.git("commit", "-m", "docs: rewrite the divergent-post-bump ticket")
    repo.push_competing_commit(
        "coga/tasks/divergent-post-bump/ticket.md",
        ticket.read_text() + "\ncontrol-only change\n",
    )

    with pytest.raises(OpenPrError, match="divergent-post-bump/ticket.md") as exc:
        open_pr(
            cfg,
            slug="divergent-post-bump",
            blackboard_path=ticket,
            single_checkout=True,
        )

    # The branch copy *is* the live ticket here, so the stranded-write wording
    # (which says to drop the branch copy) must not be offered.
    assert "stranded ticket write" not in str(exc.value)
    assert "Rebase or merge" in str(exc.value)
    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def test_open_pr_record_reaches_control_so_retry_is_not_stale(
    tmp_path, monkeypatch, real_git
):
    """The generated `pr:` record must land on control, not only the branch.

    Publishing the record to the feature branch alone leaves the ticket
    divergent between the two tips. The freshness check accepts an overlapping
    generated path only while both tips carry identical bytes, so the next run
    would reject open-pr's own record as a stale branch and wedge the
    documented idempotent retry.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(
        monkeypatch,
        bin_dir,
        create_url="https://github.com/acme/repo/pull/21",
    )

    ticket = _write_ticket(
        repo.coga_os,
        "record-retry",
        branch="record-retry",
        worktree=repo.root,
    )
    repo.git("add", "--", "coga/tasks/record-retry/ticket.md")
    repo.git("commit", "-m", "ticket: add record retry")
    repo.git("push", "origin", "main")

    repo.checkout_branch("record-retry")
    (repo.coga_os / "change.txt").write_text("a real change\n")
    repo.git("add", "--", "coga/change.txt")
    repo.git("commit", "-m", "feature: a real change")

    cfg = load_config(repo.coga_os)
    # A preceding bump advances control through generated task state. Without
    # it the retry's freshness check short-circuits on "HEAD contains latest
    # control" and never reaches the overlap classifier this guards.
    ticket.write_text(
        ticket.read_text().replace("step: 1 (open-pr)", "step: 2 (open-pr)")
    )
    sync_task_state(
        cfg, ticket.parent, message="Ticket: record-retry — step 2 (open-pr)"
    )

    url = open_pr(
        cfg,
        slug="record-retry",
        blackboard_path=ticket,
        single_checkout=True,
    )

    # The documented idempotent retry is accepted, not refused as stale.
    assert (
        open_pr(
            cfg,
            slug="record-retry",
            blackboard_path=ticket,
            single_checkout=True,
        )
        == url
    )

    # Because the record reached control.
    published = repo.git(
        "show", "refs/heads/main:coga/tasks/record-retry/ticket.md", cwd=repo.origin
    )
    assert f"pr: {url}" in published
    assert _dirty_paths(repo) == {"coga/tasks/record-retry/ticket.md"}


def test_open_pr_record_sync_refuses_to_bury_a_concurrent_close(
    tmp_path, monkeypatch, real_git, capsys
):
    """The record sync must not overwrite a ticket another checkout finished.

    `open_pr`'s terminal-status gate reads the *local* ticket, which still says
    `in_progress` here; the close is only visible in the committed control copy
    that the landing overlay is about to replace. So the guard has to run at the
    sync layer, and its refusal must stay non-fatal: the PR is already open, so
    this is exactly as survivable as a failed push.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(
        monkeypatch,
        bin_dir,
        create_url="https://github.com/acme/repo/pull/22",
    )

    slug = "closed-elsewhere"
    ticket_rel = f"coga/tasks/{slug}/ticket.md"
    ticket = _write_ticket(
        repo.coga_os, slug, branch=slug, worktree=repo.root
    )
    repo.git("add", "--", ticket_rel)
    repo.git("commit", "-m", "ticket: add closed-elsewhere")
    repo.git("push", "origin", "main")

    repo.checkout_branch(slug)
    (repo.coga_os / "change.txt").write_text("a real change\n")
    repo.git("add", "--", "coga/change.txt")
    repo.git("commit", "-m", "feature: a real change")

    # Another checkout finishes the task and lands that on control. The feature
    # branch never touched the ticket, so this stays non-overlapping generated
    # drift and the freshness gate still lets the publish through.
    repo.push_competing_commit(
        ticket_rel, ticket.read_text().replace("status: in_progress", "status: done")
    )

    url = open_pr(
        load_config(repo.coga_os),
        slug=slug,
        blackboard_path=ticket,
        single_checkout=True,
    )

    # Non-fatal: the PR was opened and its URL still comes back.
    assert url == "https://github.com/acme/repo/pull/22"

    # The finished control copy is intact — not replaced by our `pr:` write.
    control_ticket = repo.git(
        "show", f"refs/heads/main:{ticket_rel}", cwd=repo.origin
    )
    assert "status: done" in control_ticket
    assert url not in control_ticket

    # Surfaced as a refusal, not a plain sync failure, on both channels.
    assert "sync refused" in capsys.readouterr().err
    assert "sync refused" in (repo.coga_os / "log.md").read_text()

    # The local write stands; the checkout is knowingly behind control.
    assert parse_pr_url(read_blackboard(ticket)) == url


def test_open_pr_commits_single_checkout_record_from_nested_recorded_path(
    tmp_path, monkeypatch, real_git
):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(
        monkeypatch,
        bin_dir,
        create_url="https://github.com/acme/repo/pull/14",
    )

    ticket = _write_ticket(
        repo.coga_os,
        "nested-recorded-path",
        branch="nested-recorded-path",
        worktree=repo.coga_os,
    )
    repo.git("add", "--", "coga/tasks/nested-recorded-path/ticket.md")
    repo.git("commit", "-m", "ticket: add nested recorded path")
    repo.git("push", "origin", "main")
    repo.checkout_branch("nested-recorded-path")
    (repo.coga_os / "change.txt").write_text("a real change\n")
    repo.git("add", "--", "coga/change.txt")
    repo.git("commit", "-m", "feature: a real change")

    url = open_pr(
        load_config(repo.coga_os),
        slug="nested-recorded-path",
        blackboard_path=ticket,
        single_checkout=True,
    )

    assert url == "https://github.com/acme/repo/pull/14"
    assert _dirty_paths(repo) == {"coga/tasks/nested-recorded-path/ticket.md"}
    assert "Ticket: nested-recorded-path — PR opened" in repo.git(
        "log", "--format=%s", "main", cwd=repo.origin
    )


def test_open_pr_uses_annotated_quoted_dev_metadata(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    branch = "annotated-dev"
    wt = _feature_worktree(repo, tmp_path, branch, commit=True)
    ticket = _write_ticket(
        repo.coga_os,
        "annotated-metadata",
        branch=f"`{branch}` (other repo)",
        worktree=f"`{wt}` (other repo)",
    )

    url = open_pr(
        load_config(repo.coga_os),
        slug="annotated-metadata",
        blackboard_path=ticket,
    )

    assert url == "https://github.com/acme/repo/pull/7"
    assert repo.git(
        "rev-parse", "--verify", f"refs/heads/{branch}", cwd=repo.origin
    ).strip()
    assert "pr create" in log.read_text()
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


@pytest.mark.parametrize(
    "dirty_relpath",
    ["coga/uncommitted.txt", "coga/tasks/dirty/ticket.py"],
)
def test_open_pr_fails_when_worktree_dirty(tmp_path, monkeypatch, dirty_relpath):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "dirty-branch", commit=True)
    dirty_path = wt / dirty_relpath
    dirty_path.parent.mkdir(parents=True, exist_ok=True)
    dirty_path.write_text("uncommitted implementation\n")
    ticket = _write_ticket(repo.coga_os, "dirty", branch="dirty-branch", worktree=wt)

    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="uncommitted changes") as exc:
        open_pr(cfg, slug="dirty", blackboard_path=ticket)
    assert "confirmed duplicate hunks" in str(exc.value)
    assert "keep intentional ticket or attachment changes" in str(exc.value)
    assert dirty_path.read_text() == "uncommitted implementation\n"


def test_open_pr_dirty_own_ticket_steers_to_stash_not_commit(tmp_path, monkeypatch):
    """Uncommitted edits to this ticket's own file must not be committed.

    "Commit or stash" is the instruction that manufactures the committed
    duplicate one step later; for the ticket file itself the message must say
    to preserve the text in the primary ticket and stash or discard here.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "dirty-own", commit=True)
    ticket = _write_ticket(repo.coga_os, "dirty-own", branch="dirty-own", worktree=wt)
    stranded_copy = wt / "coga" / "tasks" / "dirty-own" / "ticket.md"
    stranded_copy.parent.mkdir(parents=True)
    stranded_copy.write_text(ticket.read_text() + "\nfeature-checkout note\n")

    with pytest.raises(OpenPrError, match="uncommitted changes") as exc:
        open_pr(load_config(repo.coga_os), slug="dirty-own", blackboard_path=ticket)

    message = str(exc.value)
    assert "this ticket's own file (coga/tasks/dirty-own/ticket.md)" in message
    assert "Do not commit it here" in message
    assert "git restore --staged --worktree -- coga/tasks/dirty-own/ticket.md" in message
    assert "do not stash it just to pass this gate" in message
    assert "confirmed duplicate hunks" not in message
    assert stranded_copy.read_text().endswith("feature-checkout note\n")


def test_open_pr_dirty_mixed_commits_source_but_not_own_ticket(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "dirty-mixed", commit=True)
    ticket = _write_ticket(
        repo.coga_os, "dirty-mixed", branch="dirty-mixed", worktree=wt
    )
    stranded_copy = wt / "coga" / "tasks" / "dirty-mixed" / "ticket.md"
    stranded_copy.parent.mkdir(parents=True)
    stranded_copy.write_text(ticket.read_text())
    (wt / "coga" / "uncommitted.txt").write_text("uncommitted implementation\n")

    with pytest.raises(OpenPrError, match="uncommitted changes") as exc:
        open_pr(load_config(repo.coga_os), slug="dirty-mixed", blackboard_path=ticket)

    message = str(exc.value)
    assert "Commit the implementation dirt (coga/uncommitted.txt)" in message
    assert "but not this ticket's own file (coga/tasks/dirty-mixed/ticket.md)" in message
    assert "git restore --staged --worktree -- coga/tasks/dirty-mixed/ticket.md" in message


def test_open_pr_dirty_single_checkout_preserves_live_ticket(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    ticket = _write_ticket(
        repo.coga_os,
        "dirty-single",
        branch="dirty-single",
        worktree=repo.root,
    )
    repo.git("add", "--", "coga/tasks/dirty-single/ticket.md")
    repo.git("commit", "-m", "seed live ticket")
    repo.git("push", "origin", "main")
    repo.checkout_branch("dirty-single")
    ticket.write_text(ticket.read_text() + "\n## Peer review\nFresh results.\n")
    (repo.coga_os / "notes.txt").write_text("uncommitted product work\n")
    live_bytes = ticket.read_bytes()

    with pytest.raises(OpenPrError, match="uncommitted changes") as exc:
        open_pr(
            load_config(repo.coga_os),
            slug="dirty-single",
            blackboard_path=ticket,
            single_checkout=True,
        )

    # The live ticket is excluded from the gate; the product dirt is what refused.
    assert "live task/log state is already excluded" in str(exc.value)
    assert "discard" in str(exc.value)
    assert ticket.read_bytes() == live_bytes
    assert repo.git("branch", "--show-current") == "dirty-single\n"


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
    # The note is a diagnostic, so it stays off stdout — that channel carries
    # the PR URL alone.
    assert (
        "advanced only through non-overlapping Coga task/log state"
        in capsys.readouterr().err
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
    with pytest.raises(
        OpenPrError, match="Overlapping paths: coga/tasks/shared.md"
    ) as exc:
        open_pr(cfg, slug="overlap", blackboard_path=ticket)

    # Another ticket's state, not this ticket's file: ordinary staleness
    # wording, so the operator is still told to rebase or merge.
    assert "Rebase or merge" in str(exc.value)
    assert "stranded ticket write" not in str(exc.value)
    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def _seed_ticket_on_control(repo, ticket: Path, slug: str) -> None:
    """Commit and push a ticket on `main` so a branch forked after it shares it."""
    repo.git("add", "--", f"coga/tasks/{slug}/ticket.md")
    repo.git("commit", "-m", f"ticket: seed {slug}")
    repo.git("push", "origin", "main")


def _commit_ticket_on_branch(repo, wt: Path, slug: str, text: str) -> None:
    copy = wt / "coga" / "tasks" / slug / "ticket.md"
    copy.write_text(text)
    repo.git("add", "--", f"coga/tasks/{slug}/ticket.md", cwd=wt)
    repo.git("commit", "-m", f"stranded: edit {slug} on the branch", cwd=wt)


def test_open_pr_reclassifies_own_ticket_stranded_write_and_prescribed_repair_works(
    tmp_path, monkeypatch
):
    """An own-ticket overlap is a stranded write, not staleness — and the
    prescribed repair must actually get the operator past the gate.

    The generic refusal says "rebase", which replays the stranded commit onto
    control and manufactures the `ticket.md` conflict. The reclassified message
    names the file, the diff command, and the merge-base restore; applying
    exactly that repair then lets `open_pr` succeed.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    slug = "own-stranded"
    ticket = _write_ticket(repo.coga_os, slug, branch="own-stranded", worktree="pending")
    _seed_ticket_on_control(repo, ticket, slug)

    wt = _feature_worktree(repo, tmp_path, "own-stranded", commit=True)
    ticket.write_text(ticket.read_text().replace("worktree: pending", f"worktree: {wt}"))
    _commit_ticket_on_branch(repo, wt, slug, ticket.read_text() + "\n## Dev notes\nwritten in the feature checkout\n")
    repo.push_competing_commit(
        f"coga/tasks/{slug}/ticket.md",
        ticket.read_text().replace("step: 1 (open-pr)", "step: 2 (review)"),
    )

    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="stranded ticket write") as exc:
        open_pr(cfg, slug=slug, blackboard_path=ticket)

    message = str(exc.value)
    path = f"coga/tasks/{slug}/ticket.md"
    assert f"this ticket's own file ({path})" in message
    assert "Control never received this content" in message
    assert f"git diff FETCH_HEAD HEAD -- {path}" in message
    assert (
        "git restore --staged --worktree --source=$(git merge-base FETCH_HEAD HEAD) "
        f"-- {path}" in message
    )
    assert "Do not rebase" in message
    assert "Rebase or merge" not in message
    assert not log.exists() or "pr create" not in log.read_text()

    # Apply the prescribed repair verbatim, in the feature checkout.
    merge_base = repo.git("merge-base", "FETCH_HEAD", "HEAD", cwd=wt).strip()
    repo.git(
        "restore", "--staged", "--worktree", f"--source={merge_base}", "--", path, cwd=wt
    )
    repo.git("commit", "-m", "Drop stranded ticket write", cwd=wt)

    url = open_pr(cfg, slug=slug, blackboard_path=ticket)

    assert url == "https://github.com/acme/repo/pull/7"
    assert "pr create" in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) == url


def test_open_pr_stranded_message_keeps_other_overlap_reasons(tmp_path, monkeypatch):
    """Mixed drift: the ticket remediation must not hide a source overlap."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    slug = "own-mixed"
    ticket = _write_ticket(repo.coga_os, slug, branch="own-mixed", worktree="pending")
    _seed_ticket_on_control(repo, ticket, slug)
    (repo.coga_os / "change.txt").write_text("base\n")
    repo.git("add", "--", "coga/change.txt")
    repo.git("commit", "-m", "seed source")
    repo.git("push", "origin", "main")

    wt = _feature_worktree(repo, tmp_path, "own-mixed", commit=True)
    ticket.write_text(ticket.read_text().replace("worktree: pending", f"worktree: {wt}"))
    _commit_ticket_on_branch(repo, wt, slug, ticket.read_text() + "\nbranch note\n")
    repo.push_competing_commit(f"coga/tasks/{slug}/ticket.md", ticket.read_text() + "\ncontrol\n")
    repo.push_competing_commit("coga/change.txt", "control source change\n")

    with pytest.raises(OpenPrError, match="stranded ticket write") as exc:
        open_pr(load_config(repo.coga_os), slug=slug, blackboard_path=ticket)

    message = str(exc.value)
    assert "also diverges from main on: coga/change.txt" in message
    assert "git merge FETCH_HEAD" in message


def test_open_pr_names_absorbed_ticket_copy_as_safe_to_drop(tmp_path, monkeypatch):
    """A branch copy control already absorbed is stale, not lost content.

    Bumping from the feature checkout commits the ticket on the branch and
    lands the same bytes on control; when control then moves on, the overlap
    is still refused, but the message must say the content is already there.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    slug = "own-absorbed"
    ticket = _write_ticket(repo.coga_os, slug, branch="own-absorbed", worktree="pending")
    _seed_ticket_on_control(repo, ticket, slug)

    wt = _feature_worktree(repo, tmp_path, "own-absorbed", commit=True)
    ticket.write_text(ticket.read_text().replace("worktree: pending", f"worktree: {wt}"))
    absorbed = ticket.read_text() + "\nbumped from the feature checkout\n"
    _commit_ticket_on_branch(repo, wt, slug, absorbed)
    repo.push_competing_commit(f"coga/tasks/{slug}/ticket.md", absorbed)
    repo.push_competing_commit(f"coga/tasks/{slug}/ticket.md", absorbed + "later control state\n")

    with pytest.raises(OpenPrError, match="stranded ticket write") as exc:
        open_pr(load_config(repo.coga_os), slug=slug, blackboard_path=ticket)

    assert "Control already absorbed this exact content" in str(exc.value)
    assert "Control never received" not in str(exc.value)


# --- stranded_task_state_paths unit -------------------------------------------


def _stranded_fixture(tmp_path):
    """A repo with `coga/tasks/t.md` on main and a `feat` worktree forked after it."""
    repo = init_git_repo(tmp_path)
    path = repo.coga_os / "tasks" / "t.md"
    path.write_text("base\n")
    repo.git("add", "--", "coga/tasks/t.md")
    repo.git("commit", "-m", "seed t")
    wt = tmp_path / "wt-feat"
    repo.git("worktree", "add", str(wt), "-b", "feat", "main")
    return repo, wt


def _commit_t(repo, cwd: Path, text: str, message: str) -> None:
    (cwd / "coga" / "tasks" / "t.md").write_text(text)
    repo.git("add", "--", "coga/tasks/t.md", cwd=cwd)
    repo.git("commit", "-m", message, cwd=cwd)


@pytest.mark.parametrize("control_advances", [False, True])
def test_stranded_task_state_paths_reports_branch_write_control_lacks(
    tmp_path, control_advances
):
    repo, wt = _stranded_fixture(tmp_path)
    _commit_t(repo, wt, "branch edit\n", "feat: edit t")
    if control_advances:
        _commit_t(repo, repo.root, "control edit\n", "control: advance t")

    result = stranded_task_state_paths(
        "main", "feat", ["coga/tasks/t.md"], cwd=repo.root
    )

    assert result == ("coga/tasks/t.md",)


def test_stranded_task_state_paths_ignores_branch_merely_behind_control(tmp_path):
    """Control running ahead of an untouched branch copy is the normal state."""
    repo, wt = _stranded_fixture(tmp_path)
    (wt / "coga" / "change.txt").write_text("real change\n")
    repo.git("add", "-A", cwd=wt)
    repo.git("commit", "-m", "feat: real change", cwd=wt)
    _commit_t(repo, repo.root, "control edit\n", "control: advance t")
    _commit_t(repo, repo.root, "control edit again\n", "control: advance t twice")

    result = stranded_task_state_paths(
        "main", "feat", ["coga/tasks/t.md"], cwd=repo.root
    )

    assert result == ()


def test_stranded_task_state_paths_ignores_absorbed_then_stale_copy(tmp_path):
    """A feature-side bump lands identical bytes on control; later control
    advances past them. The branch is behind, not carrying content control
    lacks — the `_refresh_committed_divergence_reason` rule."""
    repo, wt = _stranded_fixture(tmp_path)
    _commit_t(repo, wt, "bumped\n", "feat: bump t")
    _commit_t(repo, repo.root, "bumped\n", "control: absorb t")
    _commit_t(repo, repo.root, "bumped\nmoved on\n", "control: advance t")

    result = stranded_task_state_paths(
        "main", "feat", ["coga/tasks/t.md"], cwd=repo.root
    )

    assert result == ()


def test_stranded_task_state_paths_reports_branch_deletion_control_keeps(tmp_path):
    repo, wt = _stranded_fixture(tmp_path)
    repo.git("rm", "-q", "--", "coga/tasks/t.md", cwd=wt)
    repo.git("commit", "-m", "feat: delete t", cwd=wt)

    result = stranded_task_state_paths(
        "main", "feat", ["coga/tasks/t.md"], cwd=repo.root
    )

    assert result == ("coga/tasks/t.md",)


def test_stranded_task_state_paths_is_indeterminate_on_missing_ref(tmp_path):
    repo, _wt = _stranded_fixture(tmp_path)

    assert (
        stranded_task_state_paths("main", "no-such-branch", ["coga/tasks/t.md"], cwd=repo.root)
        is None
    )
    assert stranded_task_state_paths("main", "feat", [], cwd=repo.root) == ()


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


def test_open_pr_skill_has_no_executable_entrypoint() -> None:
    skill = (_LIVE_SKILL / "SKILL.md").read_text()
    assert "name: code/open-pr" in skill
    assert not (_LIVE_SKILL / "run.py").exists()
    assert not (_LIVE_SKILL / "recipe.py").exists()
    assert not (_PACKAGED_SKILL / "run.py").exists()
    assert not (_PACKAGED_SKILL / "recipe.py").exists()


def test_publishable_paths_counts_deliberate_ticket_prose(tmp_path):
    """Rewriting a ticket's description is reviewable work, not lifecycle churn.

    The blanket `coga/tasks/**` exclusion this replaces refused exactly this
    PR: a change whose whole implementation is the ticket's own prose.
    """
    repo = init_git_repo(tmp_path)
    ticket = _write_ticket(
        repo.coga_os, "prose-only", branch="prose-only", worktree=repo.root
    )
    repo.git("add", "--", "coga/tasks/prose-only/ticket.md")
    repo.git("commit", "-m", "ticket: seed prose-only")

    repo.checkout_branch("prose-only")
    ticket.write_text(
        ticket.read_text().replace(
            "The change we are shipping.", "A materially rewritten description."
        )
    )
    repo.git("add", "--", "coga/tasks/prose-only/ticket.md")
    repo.git("commit", "-m", "docs: rewrite the prose-only description")

    assert _single_checkout_publishable_paths(
        base_ref="main",
        checkout_root=repo.root,
        coga_root=repo.coga_os,
    ) == ["coga/tasks/prose-only/ticket.md"]


def test_publishable_paths_ignores_lifecycle_fields_blackboard_and_union_files(
    tmp_path,
):
    """Everything Coga writes is invisible, decided by ownership of the bytes.

    A ticket Coga only advanced, a blackboard it filled in, and a `merge=union`
    audit append are all machine state — the last one because git says the file
    takes the union driver, not because it is named here.
    """
    repo = init_git_repo(tmp_path)
    ticket = _write_ticket(
        repo.coga_os, "state-only", branch="state-only", worktree=repo.root
    )
    repo.git("add", "--", "coga/tasks/state-only/ticket.md")
    repo.git("commit", "-m", "ticket: seed state-only")

    repo.checkout_branch("state-only")
    ticket.write_text(
        ticket.read_text()
        .replace("status: in_progress", "status: done")
        .replace("step: 1 (open-pr)", "step: 2 (review)")
        .replace("assignee: claude", "assignee: marc")
        + "\nagent notes written during the step\n"
    )
    (repo.coga_os / "log.md").write_text("an audit append\n")
    repo.git(
        "add", "--", "coga/tasks/state-only/ticket.md", "coga/log.md"
    )
    repo.git("commit", "-m", "Ticket: state-only — done")

    assert (
        _single_checkout_publishable_paths(
            base_ref="main",
            checkout_root=repo.root,
            coga_root=repo.coga_os,
        )
        == []
    )


def test_publishable_paths_keeps_the_extension_marker_out_of_the_signature(
    tmp_path,
):
    """A dropped key takes its continuation lines — and nothing else.

    `Ticket.render` writes `launch_generation` immediately before the
    `# --- extensions ---` marker. That marker has no colon, so a state machine
    that carried the drop across it would swallow the marker on the head side
    only and make a ticket Coga merely advanced look hand-authored — defeating
    the gate for every repo that declares `[ticket.fields.*]`.
    """
    repo = init_git_repo(tmp_path)
    ticket = _write_ticket(
        repo.coga_os, "extended", branch="extended", worktree=repo.root
    )
    with_extensions = ticket.read_text().replace(
        "script: null\n",
        "script: null\nlaunch_generation: abc123\n# --- extensions ---\narea: infra\n",
    )
    ticket.write_text(with_extensions)
    repo.git("add", "--", "coga/tasks/extended/ticket.md")
    repo.git("commit", "-m", "ticket: seed extended")

    repo.checkout_branch("extended")
    ticket.write_text(
        with_extensions.replace("launch_generation: abc123\n", "").replace(
            "status: in_progress", "status: done"
        )
    )
    repo.git("add", "--", "coga/tasks/extended/ticket.md")
    repo.git("commit", "-m", "Ticket: extended — done")

    assert (
        _single_checkout_publishable_paths(
            base_ref="main",
            checkout_root=repo.root,
            coga_root=repo.coga_os,
        )
        == []
    )


def test_publishable_paths_fails_loud_when_git_attributes_cannot_be_read(
    tmp_path, monkeypatch
):
    """A failed `check-attr` must not read as "no union files".

    Answering "no union files" on error flips this gate from refusing a
    state-only branch to opening an empty PR, silently — the failure mode
    `coga/principles` #6 rules out.
    """
    repo = init_git_repo(tmp_path)
    _write_ticket(repo.coga_os, "probe-fails", branch="probe-fails", worktree=repo.root)
    repo.git("add", "--", "coga/tasks/probe-fails/ticket.md")
    repo.git("commit", "-m", "ticket: seed probe-fails")
    repo.checkout_branch("probe-fails")
    (repo.coga_os / "log.md").write_text("an audit append\n")
    repo.git("add", "--", "coga/log.md")
    repo.git("commit", "-m", "Log: probe-fails")

    real_run_git = coga_git.run_git

    def refuse_check_attr(root, *args, **kwargs):
        if args and args[0] == "check-attr":
            raise coga_git.GitError("`git check-attr` failed: fatal: nope")
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(coga_git, "run_git", refuse_check_attr)

    with pytest.raises(OpenPrError, match="could not read git attributes"):
        _single_checkout_publishable_paths(
            base_ref="main",
            checkout_root=repo.root,
            coga_root=repo.coga_os,
        )
