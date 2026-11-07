"""Human-review PRs for ambiguous lifecycle status conflicts.

Real Git throughout (a working clone, its bare `origin`, a peer clone); only
the `gh` boundary (`review_conflict._gh`) is faked, by a tiny in-memory PR
table keyed by head branch.
"""

from __future__ import annotations

import json
import subprocess
from itertools import permutations
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coga import git, review_conflict
from coga.commands.common import prepare_lifecycle_ticket
from coga.config import load_config
from coga.tasks import resolve_task
from coga.ticket import Ticket
from tests.test_git import _clone, _control, _lifecycle_text, _peer_writes, _seed_lifecycle


class FakeGitHub:
    """`gh pr list/create/view` over a dict of PRs; records every call."""

    def __init__(self) -> None:
        self.prs: list[dict[str, str]] = []
        self.calls: list[list[str]] = []
        self.bodies: list[str] = []
        self.fail: str | None = None
        self.repositories: list[str] = []

    def __call__(
        self, args: list[str], *, cwd: Path, repository: str, stdin: str | None = None,
    ) -> str:
        self.calls.append(args)
        self.repositories.append(repository)
        if self.fail is not None:
            raise review_conflict.ReviewUnavailable(self.fail)
        verb = args[:2]
        if verb == ["pr", "list"]:
            head = args[args.index("--head") + 1]
            return json.dumps([pr for pr in self.prs if pr["head"] == head])
        if verb == ["pr", "create"]:
            pr = {
                "number": len(self.prs) + 1,
                "url": f"https://github.test/pull/{len(self.prs) + 1}",
                "state": "OPEN",
                "title": args[args.index("--title") + 1],
                "head": args[args.index("--head") + 1],
                "base": args[args.index("--base") + 1],
            }
            self.prs.append(pr)
            self.bodies.append(stdin or "")
            return pr["url"] + "\n"
        if verb == ["pr", "view"]:
            for pr in self.prs:
                if pr["url"] == args[2]:
                    return json.dumps({"state": pr["state"]})
            raise review_conflict.ReviewUnavailable("no pull requests found")
        raise AssertionError(f"unexpected gh call {args}")

    def created(self) -> int:
        return sum(1 for call in self.calls if call[:2] == ["pr", "create"])


@pytest.fixture
def gh(monkeypatch) -> FakeGitHub:
    fake = FakeGitHub()
    monkeypatch.setattr(review_conflict, "_gh", fake)
    return fake


def _text(status: str, blackboard: str = "notes\n") -> str:
    terminal = status in {"done", "canceled"}
    return _lifecycle_text(status=status, step=None if terminal else 1, blackboard=blackboard)


def _status_conflict(git_repo, base: str, local: str, control: str) -> tuple[Path, str]:
    path, rel = _seed_lifecycle(git_repo, status=base, step=None if base in {"done", "canceled"} else 1)
    git_repo.checkout_branch("feature/status")
    path.write_text(_text(local), encoding="utf-8", newline="\n")
    _peer_writes(git_repo, rel, _text(control))
    return path, rel


def _bump(monkeypatch) -> int:
    from coga import cli

    monkeypatch.setattr("sys.argv", ["coga", "bump", "demo"])
    sweeps: list[object] = []
    monkeypatch.setattr(cli, "_sweep_coga_state", lambda cfg: sweeps.append(cfg))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert not sweeps
    return exc.value.code


def _remote_tip(git_repo, branch: str) -> str | None:
    out = git_repo.git("ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    return out.split()[0] if out.strip() else None


@pytest.mark.parametrize(
    ("base", "local", "control"),
    [
        (next(s for s in ("active", "in_progress", "draft") if s not in (local, control)),
         local, control)
        for local, control in permutations(
            ("draft", "active", "in_progress", "paused", "blocked", "done", "canceled"), 2
        )
        if {local, control} & {"paused", "blocked"} or {local, control} == {"done", "canceled"}
    ],
)
def test_an_ambiguous_status_conflict_opens_a_human_review_pr(
    git_repo, gh, monkeypatch, capsys, base, local, control,
):
    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, base, local, control)
    original = path.read_bytes()
    control_before = _control(git_repo, rel)

    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE

    # The lifecycle operation is unapplied on both sides.
    assert path.read_bytes() == original
    assert _control(git_repo, rel) == control_before
    assert gh.created() == 1
    pr = gh.prs[0]
    assert pr["title"] == "Human Review needed: demo — lifecycle merge conflict"
    assert pr["base"] == "main"
    assert pr["head"].startswith("coga/human-review/demo-")
    assert pr["url"] in capsys.readouterr().err

    # The head is the local ticket on top of the commit that introduced the base.
    git_repo.git("fetch", "--quiet", "origin")
    head = _remote_tip(git_repo, pr["head"])
    parent = git_repo.git("rev-parse", f"{head}^").strip()
    assert git_repo.git("show", f"{parent}:{rel}") == _text(base)
    assert git_repo.git("show", f"{head}:{rel}") == original.decode()
    assert git_repo.git("diff", "--name-only", parent, head).split() == [rel]
    # Merging it into control is a real Git conflict on the ticket.
    merge = subprocess.run(
        ["git", "merge-tree", "--write-tree", "origin/main", head],
        cwd=git_repo.root, capture_output=True, text=True,
    )
    assert merge.returncode == 1 and rel in merge.stdout

    body = gh.bodies[0]
    assert f"`status`: base {base!r}, this checkout {local!r}, control {control!r}" in body
    for version in (_text(base), _text(local), _text(control)):
        assert version.strip() in body
    assert "Closes ticket" not in body
    # No implementation linkage, no conflict markers, no local branch.
    assert "pr:" not in path.read_text() and "<<<<<<<" not in path.read_text()
    assert pr["head"] not in git_repo.git("branch", "--list")
    assert review_conflict.recorded(cfg, rel)[0]["url"] == pr["url"]


def test_a_repeated_conflict_reuses_the_open_pr_without_pushing(git_repo, gh, monkeypatch, capsys):
    path, rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    branch = gh.prs[0]["head"]
    # A human pushes an edit onto the review branch.
    human = _clone(git_repo, "human-clone")
    git_repo.git("checkout", "--quiet", branch, cwd=human)
    (human / rel).write_text(_text("paused", "human edit\n"), encoding="utf-8", newline="\n")
    git_repo.git("commit", "-qam", "human edit", cwd=human)
    git_repo.git("push", "--quiet", "origin", branch, cwd=human)
    human_tip = _remote_tip(git_repo, branch)
    capsys.readouterr()

    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE

    assert gh.created() == 1
    assert _remote_tip(git_repo, branch) == human_tip
    assert "is still open" in capsys.readouterr().err


def test_a_review_branch_without_a_pr_is_reused_not_force_pushed(git_repo, gh, monkeypatch):
    _path, _rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    branch, tip = gh.prs[0]["head"], _remote_tip(git_repo, gh.prs[0]["head"])
    gh.prs.clear()

    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE

    assert gh.created() == 2 and gh.prs[0]["head"] == branch
    assert _remote_tip(git_repo, branch) == tip


def test_a_closed_review_pr_refuses_without_a_new_one(git_repo, gh, monkeypatch, capsys):
    _status_conflict(git_repo, "in_progress", "done", "canceled")
    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    gh.prs[0]["state"] = "CLOSED"
    capsys.readouterr()

    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE

    assert gh.created() == 1
    assert "closed unmerged; no new PR was opened" in capsys.readouterr().err


def test_unavailable_github_keeps_the_local_refusal_and_says_no_pr_exists(
    git_repo, gh, monkeypatch, capsys,
):
    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, "in_progress", "blocked", "done")
    original = path.read_bytes()
    gh.fail = "gh auth: not logged in"

    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE

    err = capsys.readouterr().err
    assert "human must decide" in err
    assert "No human-review PR was created: gh auth: not logged in" in err
    assert path.read_bytes() == original
    assert not git_repo.git("ls-remote", "--heads", "origin", "coga/human-review/*").strip()
    assert not review_conflict.recorded(cfg, rel)


def test_a_failed_push_reports_that_no_pr_was_created(git_repo, gh, monkeypatch, capsys):
    _status_conflict(git_repo, "active", "paused", "in_progress")
    hook = git_repo.origin / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'permission denied' >&2\nexit 1\n", encoding="utf-8", newline="\n")
    hook.chmod(0o755)

    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE

    assert gh.created() == 0
    err = capsys.readouterr().err
    assert "No human-review PR was created:" in err and "git push" in err


def _human_merges(git_repo, branch: str, rel: str, resolution: str | None) -> None:
    """Merge the review branch on control; `None` keeps control's copy."""
    human = git_repo.origin.parent / "human-merge"
    if not human.exists():
        _clone(git_repo, "human-merge")
    git_repo.git("pull", "--quiet", "--ff-only", "origin", "main", cwd=human)
    git_repo.git("fetch", "--quiet", "origin", branch, cwd=human)
    if resolution is None:
        git_repo.git("merge", "--quiet", "-s", "ours", "-m", "keep control", "FETCH_HEAD", cwd=human)
    else:
        subprocess.run(["git", "merge", "--quiet", "FETCH_HEAD"], cwd=human, capture_output=True)
        (human / rel).write_text(resolution, encoding="utf-8", newline="\n")
        git_repo.git("add", rel, cwd=human)
        git_repo.git("commit", "--quiet", "-m", "resolve", cwd=human)
    git_repo.git("push", "--quiet", "origin", "main", cwd=human)


def _prepare_and_write(cfg, path: Path) -> git.PreparedTicket:
    prepared = prepare_lifecycle_ticket(cfg, resolve_task(cfg, "demo"))
    git.write_ticket(cfg, prepared.ticket, path, prepared=prepared)
    return prepared


def test_a_merged_review_pr_is_adopted_and_recorded_as_provenance(git_repo, gh, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    resolution = _text("paused", "notes\nhuman resolution\n")
    _human_merges(git_repo, gh.prs[0]["head"], rel, resolution)
    gh.prs[0]["state"] = "MERGED"

    prepared = _prepare_and_write(cfg, path)

    assert prepared.outcome == "adopted"
    assert path.read_text() == resolution
    assert not review_conflict.recorded(cfg, rel)
    published = git_repo.git("rev-parse", f"{git.PUBLISHED_REF}:{rel}").strip()
    assert published == git_repo.git("rev-parse", f"origin/main:{rel}").strip()
    # The next preparation sees an ordinary, unconflicted ticket.
    assert git.prepare_ticket(cfg, path).outcome == "same"


def test_local_edits_after_the_review_pr_merge_onto_its_resolution(git_repo, gh, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    path.write_text(_text("paused", "notes\nlater local note\n"), encoding="utf-8", newline="\n")
    _human_merges(git_repo, gh.prs[0]["head"], rel, _text("in_progress", "human note\nnotes\n"))
    gh.prs[0]["state"] = "MERGED"

    prepared = _prepare_and_write(cfg, path)

    assert prepared.outcome == "merged"
    ticket = Ticket.read(path)
    assert ticket.status == "in_progress"
    assert "human note" in ticket.body and "later local note" in ticket.body
    assert not review_conflict.recorded(cfg, rel)


def test_a_merge_keeping_controls_copy_resolves_the_same_conflict_anywhere(
    git_repo, gh, monkeypatch,
):
    """`-s ours` leaves control's blob unchanged: the same conflict key now
    finds a merged PR, even in a checkout with no local record."""
    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, "in_progress", "done", "canceled")
    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    _human_merges(git_repo, gh.prs[0]["head"], rel, None)
    gh.prs[0]["state"] = "MERGED"
    review_conflict.forget(cfg, rel)

    prepared = _prepare_and_write(cfg, path)

    assert prepared.outcome == "adopted"
    assert Ticket.read(path).status == "canceled"
    assert gh.created() == 1


def test_a_non_status_conflict_never_opens_a_review_pr(git_repo, gh, monkeypatch):
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/body")
    path.write_text(_lifecycle_text(blackboard="local rewrite\n"), encoding="utf-8", newline="\n")
    _peer_writes(git_repo, rel, _lifecycle_text(blackboard="peer rewrite\n"))

    assert _bump(monkeypatch) == git.RETRY_WITHOUT_SWEEP_EXIT_CODE

    assert gh.calls == []


def test_review_titles_are_recognized():
    assert review_conflict.is_review_title(review_conflict.title("v1/demo"))
    assert not review_conflict.is_review_title("[deep · A:claude R:none] Fix demo")


def test_unblock_all_opens_review_and_adopts_its_merged_resolution(git_repo, gh):
    from coga.cli import app

    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, "active", "blocked", "in_progress")
    original = path.read_bytes()
    result = CliRunner().invoke(app, ["unblock", "--all"], input="answer\n")
    assert result.exit_code == 75, result.output
    assert gh.created() == 1 and gh.prs[0]["url"] in result.output
    assert path.read_bytes() == original

    resolution = _text("blocked", "## Blockers\n\n- [ ] [2026-11-05 10:00] "
                       "[human:marc] id=20261105T100000 Need input\n")
    _human_merges(git_repo, gh.prs[0]["head"], rel, resolution)
    gh.prs[0]["state"] = "MERGED"
    result = CliRunner().invoke(app, ["unblock", "--all"], input="answer\n")
    assert result.exit_code == 0, result.output
    assert Ticket.read(path).status == "active"
    assert "- [x]" in path.read_text(encoding="utf-8")
    assert not review_conflict.recorded(cfg, rel)


def test_unblock_after_prompt_escalates_a_new_status_conflict(git_repo, gh, monkeypatch):
    from coga.cli import app
    from tests.test_git import _lifecycle_text

    path, rel = _seed_lifecycle(git_repo, status="active")
    git_repo.checkout_branch("feature/unblock-prompt")
    path.write_text(
        _lifecycle_text(status="blocked", blackboard="## Blockers\n\n- [ ] "
                        "[2026-11-05 10:00] [human:marc] id=20261105T100000 Need input\n"),
        encoding="utf-8", newline="\n",
    )
    original = path.read_bytes()

    def answer(*args, **kwargs):
        _peer_writes(git_repo, rel, _text("in_progress"))
        return "answer"

    monkeypatch.setattr("typer.prompt", answer)
    result = CliRunner().invoke(app, ["unblock", "demo"])
    assert result.exit_code == 75, result.output
    assert gh.created() == 1 and gh.prs[0]["url"] in result.output
    assert path.read_bytes() == original


def test_owner_retires_merged_review_only_after_confirmed_publication(git_repo, gh, monkeypatch):
    from coga.cli import app

    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    assert _bump(monkeypatch) == 75
    resolution = _text("paused", "notes\nhuman resolution\n")
    _human_merges(git_repo, gh.prs[0]["head"], rel, resolution)
    gh.prs[0]["state"] = "MERGED"
    result = CliRunner().invoke(app, ["owner", "demo", "alice"])
    assert result.exit_code == 0, result.output
    assert not review_conflict.recorded(cfg, rel)
    assert git_repo.git("rev-parse", f"{git.PUBLISHED_REF}:{rel}") == git_repo.git(
        "rev-parse", f"origin/main:{rel}"
    )

    newer = Ticket.read(path)
    newer.frontmatter["owner"] = "bob"
    _peer_writes(git_repo, rel, newer.render())
    prepared = prepare_lifecycle_ticket(cfg, resolve_task(cfg, "demo"))
    assert prepared.outcome == "adopted" and prepared.ticket.owner == "bob"


def test_failed_owner_publication_keeps_review_for_retry(git_repo, gh, monkeypatch):
    from coga.cli import app

    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    original = path.read_bytes()
    assert _bump(monkeypatch) == 75
    _human_merges(git_repo, gh.prs[0]["head"], rel, _text("paused", "human resolution\n"))
    gh.prs[0]["state"] = "MERGED"
    # Git runs the hook through its bundled sh on Windows too.
    hook = git_repo.origin / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8", newline="\n")
    hook.chmod(0o755)
    result = CliRunner().invoke(app, ["owner", "demo", "alice"])
    assert result.exit_code == 75, result.output
    assert path.read_bytes() == original
    assert review_conflict.recorded(cfg, rel)
    hook.unlink()
    result = CliRunner().invoke(app, ["owner", "demo", "alice"])
    assert result.exit_code == 0, result.output
    assert not review_conflict.recorded(cfg, rel)


def test_review_tool_permission_error_preserves_refusal(git_repo, gh, monkeypatch, capsys):
    path, rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    original, control = path.read_bytes(), _control(git_repo, rel)

    def denied(*args, **kwargs):
        raise PermissionError("cannot execute gh")

    monkeypatch.setattr(review_conflict, "_gh", denied)
    assert _bump(monkeypatch) == 75
    assert "No human-review PR was created: cannot execute gh" in capsys.readouterr().err
    assert path.read_bytes() == original and _control(git_repo, rel) == control


def test_review_record_is_never_published_without_an_ignore_rule(git_repo, gh, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    path, rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    assert _bump(monkeypatch) == 75
    path.write_text(_control(git_repo, rel), encoding="utf-8", newline="\n")
    git.sync_coga_state(cfg)
    tracked = git_repo.git("ls-tree", "-r", "--name-only", "main", cwd=git_repo.origin)
    assert "coga/.coga/human-review.json" not in tracked.splitlines()
    assert review_conflict.recorded(cfg, rel)


def test_review_uses_configured_remote_and_control_branch(git_repo, gh):
    from dataclasses import replace

    path, rel = _status_conflict(git_repo, "active", "paused", "in_progress")
    git_repo.git("remote", "rename", "origin", "control")
    git_repo.git("remote", "add", "origin", str(git_repo.origin.parent / "wrong.git"))
    git_repo.git("fetch", "control", "main")
    git_repo.git("push", "control", "refs/remotes/control/main:refs/heads/integration")
    cfg = replace(load_config(git_repo.coga_os), git_remote="control", git_control_branch="integration")
    with pytest.raises(SystemExit) as exc:
        prepare_lifecycle_ticket(cfg, resolve_task(cfg, "demo"))
    assert exc.value.code == 75
    assert gh.created() == 1 and gh.prs[0]["base"] == "integration"
    assert gh.repositories and set(gh.repositories) == {str(git_repo.origin)}


def test_review_refuses_a_remote_with_a_different_push_destination(git_repo, gh, monkeypatch, capsys):
    _status_conflict(git_repo, "active", "paused", "in_progress")
    git_repo.git("config", "remote.origin.pushurl", "https://github.test/other/repo.git")
    assert _bump(monkeypatch) == 75
    assert not gh.calls
    assert "must fetch and push one matching repository" in capsys.readouterr().err


@pytest.mark.parametrize("source", [
    "git@github.test:Team/Repo.git", "https://github.test/Team/Repo.git",
])
def test_gh_boundary_selects_the_explicit_repository(tmp_path, monkeypatch, source):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "[]", "")

    monkeypatch.setattr(subprocess, "run", run)
    assert review_conflict._gh(["pr", "list"], cwd=tmp_path, repository=source) == "[]"
    assert calls == [["gh", "pr", "list", "--repo", "github.test/team/repo"]]
