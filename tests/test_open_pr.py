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
import sys

import yaml
from pathlib import Path
from textwrap import dedent

import pytest

from conftest import init_git_repo
from coga.autoclose import parse_pr_url, parse_worktree_path
from coga.config import load_config
from coga.github_preflight import CheckResult, stranded_task_state_paths
from coga.taskfile import read_blackboard
from coga.ticket import Ticket

from coga.open_pr import (
    OpenPrError,
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
    edit_error: bool = False,
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
            f"""\
            #!{sys.executable}
            import json
            import sys
            from pathlib import Path
            args = sys.argv[1:]
            view = Path({str(view_file)!r})
            body = ""
            if "--body-file" in args:
                body = Path(args[args.index("--body-file") + 1]).read_text()
            elif "--body" in args:
                body = args[args.index("--body") + 1]
            with Path({str(log)!r}).open("a") as out:
                out.write(" ".join(args) + "\\n" + body + "\\n")
            if args[:2] == ["pr", "view"]:
                if not view.exists():
                    sys.exit(1)
                print(view.read_text())
            elif args[:2] in (["pr", "create"], ["pr", "edit"]):
                if args[1] == "edit" and {edit_error!r}:
                    print("edit refused", file=sys.stderr)
                    sys.exit(1)
                data = json.loads(view.read_text()) if view.exists() else {{
                    "url": {create_url!r}, "state": "OPEN", "isDraft": False,
                    "baseRefName": "main",
                }}
                data.update(title=args[args.index("--title") + 1], body=body)
                view.write_text(json.dumps(data))
                if args[1] == "create":
                    print(data["url"])
            """
        )
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
    """Missing preparation includes the request and makes evidence gaps explicit."""
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
    assert "[deep · A:unknown R:unknown]" in calls
    assert "No check evidence or omission reason recorded" in calls
    assert "No independent review performed" in calls
    assert "Explanation missing" in calls


def test_open_pr_readies_existing_draft(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/3")
    wt = _feature_worktree(repo, tmp_path, "feature-draft", commit=True)
    ticket = _write_ticket(repo.coga_os, "ready-draft", branch="feature-draft", worktree=wt)

    cfg = load_config(repo.coga_os)
    open_pr(cfg, slug="ready-draft", blackboard_path=ticket)
    view_file = bin_dir / "view.json"
    data = json.loads(view_file.read_text())
    data["isDraft"] = True
    view_file.write_text(json.dumps(data))
    log.write_text("")
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


def test_open_pr_fails_when_recorded_branch_is_not_a_local_ref(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    # A branch recorded but never created in this checkout.
    ticket = _write_ticket(repo.coga_os, "no-ref", branch="feature-z", worktree=None)
    cfg = load_config(repo.coga_os)
    with pytest.raises(OpenPrError, match="does not exist in this checkout"):
        open_pr(cfg, slug="no-ref", blackboard_path=ticket)


# --- by-ref: branch recorded alone, checked from `main` -------------------------


def _feature_branch(repo, branch: str, *, commit: bool) -> None:
    """Commit on `branch` in the primary checkout, then return it to `main`.

    The `dev/checkouts` end-of-step shape: the branch exists as a ref and
    nothing holds it checked out.
    """
    repo.checkout_branch(branch)
    if commit:
        (repo.coga_os / "change.txt").write_text("a real change\n")
        repo.git("add", "--", "coga/change.txt")
        repo.git("commit", "-m", "feature: a real change")
    repo.git("switch", "main")


def test_open_pr_pushes_branch_by_name_from_main(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/8")
    _feature_branch(repo, "by-ref", commit=True)
    ticket = _write_ticket(repo.coga_os, "by-ref", branch="by-ref", worktree=None)

    url = open_pr(load_config(repo.coga_os), slug="by-ref", blackboard_path=ticket)

    assert url == "https://github.com/acme/repo/pull/8"
    assert repo.git("rev-parse", "refs/heads/by-ref", cwd=repo.origin) == repo.git(
        "rev-parse", "refs/heads/by-ref"
    )
    assert "pr create --base main --head by-ref" in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) == url
    # Never entered the branch: the checkout is still on `main`.
    assert repo.git("branch", "--show-current") == "main\n"


def test_open_pr_treats_legacy_primary_worktree_as_by_ref(tmp_path, monkeypatch):
    """A `worktree:` naming this checkout (retired single-checkout layout) is
    ignored, so a checkout back on `main` still publishes the branch."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    _feature_branch(repo, "legacy", commit=True)
    ticket = _write_ticket(repo.coga_os, "legacy", branch="legacy", worktree=repo.root)

    url = open_pr(load_config(repo.coga_os), slug="legacy", blackboard_path=ticket)

    assert parse_pr_url(read_blackboard(ticket)) == url


def test_open_pr_by_ref_fails_when_no_commits_ahead(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    _feature_branch(repo, "empty-ref", commit=False)
    ticket = _write_ticket(repo.coga_os, "empty-ref", branch="empty-ref", worktree=None)

    with pytest.raises(OpenPrError, match="no commits ahead"):
        open_pr(load_config(repo.coga_os), slug="empty-ref", blackboard_path=ticket)

    assert not log.exists() or "pr create" not in log.read_text()


def test_open_pr_by_ref_fails_on_material_stale_drift(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    _feature_branch(repo, "stale-ref", commit=True)
    (repo.root / "README.md").write_text("control moved on\n")
    repo.git("add", "--", "README.md")
    repo.git("commit", "-m", "control: source change")
    repo.git("push", "origin", "main")
    ticket = _write_ticket(repo.coga_os, "stale-ref", branch="stale-ref", worktree=None)

    with pytest.raises(OpenPrError, match="refs/heads/stale-ref does not contain latest"):
        open_pr(load_config(repo.coga_os), slug="stale-ref", blackboard_path=ticket)

    assert not log.exists() or "pr create" not in log.read_text()


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
    """Uncommitted edits to this ticket's own file are inspected, not committed.

    "Commit or stash" is the instruction that manufactures the committed
    duplicate one step later; for the ticket file itself the message must say
    to move every wanted change, an intentional authored-body edit included,
    to the live ticket and discard the clone copy: control already rewrote
    this path, so a branch commit is an overlapping stranded write.
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
    assert "Do not commit it here unchecked" in message
    assert "Inspect the diff first" in message
    assert "git restore --staged --worktree -- coga/tasks/dirty-own/ticket.md" in message
    assert "do not commit or stash it just to pass this gate" in message
    assert "intentional change to the authored ticket body" in message
    assert "into the live ticket in the primary checkout" in message
    assert "discard the clone's copy" in message
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
    assert (
        "but not this ticket's own file (coga/tasks/dirty-mixed/ticket.md) unchecked"
        in message
    )
    assert "git restore --staged --worktree -- coga/tasks/dirty-mixed/ticket.md" in message


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


# --- presentation evidence and safe refresh ----------------------------------


def _preparation(repo, wt: Path, *, depth: str = "skim") -> dict:
    head = repo.git("rev-parse", "HEAD", cwd=wt).strip()
    base = repo.git("merge-base", "main", "HEAD", cwd=wt).strip()
    return {
        "title": "Explain the changed behavior", "author": "codex",
        "author_evidence": "Codex implemented this change in the attended session.",
        "head": head, "base": base, "depth": depth,
        "rationale": "Bounded change with reviewed failure-path coverage.",
        "implementation": "Make the requested behavior visible.",
        "deviations": "None.", "limitations": "No live service check needed.",
        "files": {"coga/change.txt": "Describe the new behavior."},
        "review": {"reviewer": "claude", "kind": "independent", "status": "passed",
                   "head": head, "base": base, "detail": "Returned; no findings."},
        "checks": [{"command": "python -m pytest tests/test_change.py", "status": "passed",
                    "head": head, "base": base, "detail": "3 passed."}],
    }


def _prepared_ticket(repo, wt: Path, preparation: dict) -> Path:
    return _write_ticket(
        repo.coga_os, "presentation", branch="presentation", worktree=wt,
        pr_section="```yaml\n" + yaml.safe_dump(preparation, sort_keys=False) + "```",
    )


@pytest.mark.parametrize("depth", ["merge", "skim", "deep"])
def test_open_pr_renders_prepared_depth_and_actual_identities(tmp_path, monkeypatch, depth):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    ticket = _prepared_ticket(repo, wt, _preparation(repo, wt, depth=depth))
    open_pr(load_config(repo.coga_os), slug="presentation", blackboard_path=ticket)
    data = json.loads((bin_dir / "view.json").read_text())
    assert data["title"] == f"[{depth} · A:codex R:claude] Explain the changed behavior"
    assert "3 passed." in data["body"]
    assert "Describe the new behavior." in data["body"]
    assert "Ship the change" in data["body"]  # verbatim original title
    assert "author_evidence:" not in data["body"]  # no recursive preparation


def test_open_pr_invalidates_evidence_after_later_commit(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    prep = _preparation(repo, wt, depth="merge")
    ticket = _prepared_ticket(repo, wt, prep)
    (wt / "coga" / "change.txt").write_text("later untested behavior\n")
    repo.git("add", "coga/change.txt", cwd=wt)
    repo.git("commit", "-m", "Later edit", cwd=wt)
    open_pr(load_config(repo.coga_os), slug="presentation", blackboard_path=ticket)
    data = json.loads((bin_dir / "view.json").read_text())
    assert data["title"].startswith("[deep · A:unknown R:unknown]")
    assert "stale" in data["body"].lower()
    assert "3 passed." not in data["body"]


def test_open_pr_refreshes_generated_content_preserving_human_notes(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    prep = _preparation(repo, wt)
    ticket = _prepared_ticket(repo, wt, prep)
    cfg = load_config(repo.coga_os)
    open_pr(cfg, slug="presentation", blackboard_path=ticket)
    view_file = bin_dir / "view.json"
    data = json.loads(view_file.read_text())
    data["body"] = "Owner introduction.\n\n" + data["body"] + "\nOwner notes.\n"
    view_file.write_text(json.dumps(data))
    prep["title"] = "A more precise change title"
    prep["rationale"] = "Updated explanation."
    _prepared_ticket(repo, wt, prep)
    ticket.write_text(ticket.read_text().replace("The change we are shipping.", "Updated literal request."))
    open_pr(cfg, slug="presentation", blackboard_path=ticket)
    data = json.loads(view_file.read_text())
    assert data["title"].endswith("A more precise change title")
    assert "Updated explanation." in data["body"]
    assert "Updated literal request." in data["body"]
    assert data["body"].startswith("Owner introduction.")
    assert data["body"].endswith("Owner notes.\n")
    log.write_text("")
    open_pr(cfg, slug="presentation", blackboard_path=ticket)
    assert "pr edit" not in log.read_text()


@pytest.mark.parametrize("edit", ["title", "body", "legacy", "base"])
def test_open_pr_refuses_human_edits_before_push(tmp_path, monkeypatch, edit):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    ticket = _prepared_ticket(repo, wt, _preparation(repo, wt))
    cfg = load_config(repo.coga_os)
    open_pr(cfg, slug="presentation", blackboard_path=ticket)
    view_file = bin_dir / "view.json"
    data = json.loads(view_file.read_text())
    if edit == "title":
        data["title"] = "Human title"
    elif edit == "body":
        data["body"] = data["body"].replace("3 passed.", "Human correction.")
    elif edit == "legacy":
        data["body"] = "Legacy human description."
    else:
        data["baseRefName"] = "release"
    view_file.write_text(json.dumps(data))
    old_remote = repo.git("rev-parse", "refs/heads/presentation", cwd=repo.origin)
    (wt / "coga/change.txt").write_text("later change\n")
    repo.git("add", "coga/change.txt", cwd=wt)
    repo.git("commit", "-m", "Later change", cwd=wt)
    log.write_text("")
    with pytest.raises(OpenPrError, match="presentation|base"):
        open_pr(cfg, slug="presentation", blackboard_path=ticket)
    assert repo.git("rev-parse", "refs/heads/presentation", cwd=repo.origin) == old_remote
    assert "pr edit" not in log.read_text()
    assert json.loads(view_file.read_text()) == data


@pytest.mark.parametrize(
    ("case", "label", "expected"),
    [
        ("no-review", "deep", "No independent review performed"),
        ("self-review", "skim", "R:codex(self)"),
        ("unknown-author", "deep", "A:unknown"),
        ("unknown-reviewer", "deep", "R:unknown"),
        ("unknown-self-reviewer", "deep", "R:unknown(self)"),
        ("none-reviewer", "deep", "No completed, identified review"),
        ("stale-review", "deep", "Historical passed"),
        ("stale-check", "deep", "Historical passed"),
        ("failed-check", "deep", "failed"),
        ("pending-check", "deep", "pending"),
        ("not-run", "skim", "Workflow permits focused checks"),
        ("missing-reason", "deep", "no recorded result or omission reason"),
        ("missing-checks", "deep", "No check evidence"),
        ("missing-path", "deep", "Explanation missing"),
        ("extra-path", "deep", "Prepared paths outside this diff"),
        ("merge-self-review", "deep", "requires independent review"),
    ],
)
def test_open_pr_discloses_verification_gaps(tmp_path, case, label, expected):
    from coga.open_pr import _pr_presentation
    from coga.taskfile import split_body

    repo = init_git_repo(tmp_path)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    prep = _preparation(repo, wt)
    if case == "no-review":
        prep["review"] = {"kind": "none", "status": "not-run", "detail": "Workflow has no code-review step."}
    elif case in {"self-review", "merge-self-review"}:
        prep["review"].update(kind="self", reviewer="codex")
        if case == "merge-self-review":
            prep["depth"] = "merge"
    elif case == "unknown-author":
        prep.pop("author_evidence")
    elif case == "unknown-reviewer":
        prep["review"].pop("reviewer")
    elif case == "unknown-self-reviewer":
        prep["review"].update(kind="self", reviewer="unknown")
    elif case == "none-reviewer":
        prep["review"]["reviewer"] = "none"
    elif case == "stale-review":
        prep["review"]["head"] = "0" * 40
    elif case == "stale-check":
        prep["checks"][0]["base"] = "0" * 40
    elif case in {"failed-check", "pending-check"}:
        prep["checks"][0]["status"] = case.split("-")[0]
    elif case == "not-run":
        prep["checks"].append({"command": "python -m pytest", "status": "not-run",
                               "detail": "Workflow permits focused checks; no runtime change."})
    elif case == "missing-reason":
        prep["checks"][0].update(status="not-run", detail="")
    elif case == "missing-checks":
        prep["checks"] = []
    elif case == "missing-path":
        prep["files"] = {}
    elif case == "extra-path":
        prep["files"]["coga/not-changed.txt"] = "Old explanation."
    ticket = Ticket.read(_prepared_ticket(repo, wt, prep))
    above, blackboard = split_body(ticket.body)
    title, body = _pr_presentation(ticket, blackboard, above, "presentation",
                                   head=prep["head"], base=prep["base"],
                                   changes=[("A", ["coga/change.txt"])])
    assert title.startswith(f"[{label} ·")
    assert expected in title + body


def test_open_pr_snapshot_preserves_literal_sections_and_ignores_fenced_headings(tmp_path):
    from coga.open_pr import _pr_presentation

    repo = init_git_repo(tmp_path)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    prep = _preparation(repo, wt)
    ticket = Ticket.read(_prepared_ticket(repo, wt, prep))
    description = "## Description\n\nExact  wording.  \n\n```markdown\n## PR\nNot preparation.\n```\n\n"
    context = "## Context\n\n### Nested heading\nKeep [this](file.py) verbatim.\n\n"
    above = description + "## Acceptance\nNot in the snapshot.\n\n" + context
    title, body = _pr_presentation(ticket, "", above, "presentation",
                                   head=prep["head"], base=prep["base"], changes=[])
    assert description in body
    assert context in body
    assert "Not in the snapshot" not in body
    assert "status: in_progress" not in body
    assert "## Dev\n" not in body
    assert "````markdown\n# Ship the change" in body
    assert title.startswith("[deep · A:unknown R:unknown]")


def test_open_pr_lists_add_delete_and_both_rename_paths(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    (repo.coga_os / "old name.txt").write_text("stable rename content\n")
    (repo.coga_os / "delete.txt").write_text("obsolete\n")
    repo.git("add", "coga/old name.txt", "coga/delete.txt")
    repo.git("commit", "-m", "Base files")
    repo.git("push", "origin", "main")
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    repo.git("mv", "coga/old name.txt", "coga/new | name.txt", cwd=wt)
    repo.git("rm", "coga/delete.txt", cwd=wt)
    repo.git("commit", "-m", "Rename and delete", cwd=wt)
    prep = _preparation(repo, wt)
    prep["files"].update({"coga/old name.txt": "Rename the documented example.",
                          "coga/new | name.txt": "Rename the documented example.",
                          "coga/delete.txt": "Remove obsolete instructions."})
    ticket = _prepared_ticket(repo, wt, prep)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir)
    open_pr(load_config(repo.coga_os), slug="presentation", blackboard_path=ticket)
    body = json.loads((bin_dir / "view.json").read_text())["body"]
    assert "<code>coga/old name.txt</code> | R100 | Rename" in body
    assert "<code>coga/new &#124; name.txt</code> | R100 | Rename" in body
    assert "<code>coga/delete.txt</code> | D | Remove" in body
    assert "<code>coga/change.txt</code> | A | Describe" in body


@pytest.mark.parametrize("yaml_text", ["- item", "checks: [broken", "title: [wrong type]"])
def test_open_pr_rejects_malformed_preparation(tmp_path, monkeypatch, yaml_text):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    prep = _preparation(repo, wt)
    # Matching revisions ensure field types, not freshness, are being checked.
    prefix = f"head: {prep['head']}\nbase: {prep['base']}\n" if yaml_text.startswith("title:") else ""
    ticket = _write_ticket(repo.coga_os, "presentation", branch="presentation", worktree=wt,
                           pr_section="```yaml\n" + prefix + yaml_text + "\n```")
    with pytest.raises(OpenPrError, match="PR presentation"):
        open_pr(load_config(repo.coga_os), slug="presentation", blackboard_path=ticket)
    assert "pr create" not in log.read_text()
    assert repo.git("ls-remote", "--heads", "origin", "presentation").strip() == ""


def test_open_pr_refuses_failed_refresh_without_readying_draft_or_recording(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir, edit_error=True)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    prep = _preparation(repo, wt)
    ticket = _prepared_ticket(repo, wt, prep)
    cfg = load_config(repo.coga_os)
    open_pr(cfg, slug="presentation", blackboard_path=ticket)
    view_file = bin_dir / "view.json"
    original = json.loads(view_file.read_text())
    original["isDraft"] = True
    view_file.write_text(json.dumps(original))
    prep["title"] = "Updated title"
    _prepared_ticket(repo, wt, prep)  # no pr: yet for this retry
    log.write_text("")
    with pytest.raises(OpenPrError, match="gh pr edit failed"):
        open_pr(cfg, slug="presentation", blackboard_path=ticket)
    assert "pr ready" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None
    assert json.loads(view_file.read_text()) == original


def test_open_pr_rechecks_human_edits_after_push(tmp_path, monkeypatch):
    import coga.open_pr as module

    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    ticket = _prepared_ticket(repo, wt, _preparation(repo, wt))
    cfg = load_config(repo.coga_os)
    open_pr(cfg, slug="presentation", blackboard_path=ticket)
    real_git = module._git

    def edit_during_push(args, *, cwd):
        result = real_git(args, cwd=cwd)
        if args[0] == "push":
            view_file = bin_dir / "view.json"
            data = json.loads(view_file.read_text())
            data["title"] = "Concurrent human edit"
            view_file.write_text(json.dumps(data))
        return result

    monkeypatch.setattr(module, "_git", edit_during_push)
    log.write_text("")
    with pytest.raises(OpenPrError, match="presentation conflict"):
        open_pr(cfg, slug="presentation", blackboard_path=ticket)
    assert "pr edit" not in log.read_text()



def test_open_pr_refresh_allows_literal_marker_examples_in_snapshot(tmp_path):
    from coga.open_pr import _pr_presentation, _refresh_body
    from coga.taskfile import split_body

    repo = init_git_repo(tmp_path)
    wt = _feature_worktree(repo, tmp_path, "presentation", commit=True)
    prep = _preparation(repo, wt)
    ticket = Ticket.read(_prepared_ticket(repo, wt, prep))
    above, blackboard = split_body(ticket.body)
    above += "\n## Context\n\nLiteral closing marker: <!-- /coga:pr -->\n"
    above += "<!-- coga:pr:v1 title=" + "0" * 64 + " body=" + "0" * 64 + " -->\n"
    title, body = _pr_presentation(ticket, blackboard, above, "presentation",
                                   head=prep["head"], base=prep["base"],
                                   changes=[("A", ["coga/change.txt"])])
    existing = {"title": title, "body": body, "baseRefName": "main"}
    assert _refresh_body(existing, title, body, "main") == body
    assert "Literal closing marker: <!-- /coga:pr -->" in body
