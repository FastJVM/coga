"""Tests for the `coga open-pr` command surface — the registered `open-pr`
recipe, invoked as `coga run open-pr <slug>` (which the `open-pr` default
alias spells `coga open-pr <slug>`).

`open_pr()` itself is covered by `test_open_pr.py`; here we exercise the
entrypoint: it resolves the task from ordinary recipe argv, applies the
checkout gate, prints the bare URL on stdout, and maps an `OpenPrError` (or a
wrong-checkout refusal) to a non-zero exit. The headline case is the one the
original ticket calls out explicitly — pushing the recorded `## Dev` branch
**by name** is agnostic to which feature worktree holds it. The command itself
stays on the primary control checkout so task resolution and the blackboard
write are authoritative.

Mirrors `test_open_pr.py`'s real-git harness (a bare `origin` + a fake `gh` on
PATH) so push/PR behaviour is exercised for real without a network.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

import coga
from conftest import init_git_repo
from coga.autoclose import parse_pr_url
from coga.cli import app, main
from coga.open_pr import run_open_pr_recipe
from coga.paths import packaged_template_path
from coga.repl_supervisor import EXPECTED_TASK_ENV
from coga.runner import RECIPES
from coga.taskfile import read_blackboard


# --- fixtures / helpers (mirrors test_open_pr.py) -----------------------------


def _install_fake_gh(
    monkeypatch: pytest.MonkeyPatch,
    bin_dir: Path,
    *,
    create_url: str = "https://github.com/acme/repo/pull/7",
) -> Path:
    """Put a fake `gh` on PATH; `pr view` says no PR, `pr create` prints the URL."""
    log = bin_dir / "gh-calls.log"
    gh = bin_dir / "gh"
    gh.write_text(
        dedent(
            f"""
            #!/usr/bin/env bash
            echo "$@" >> {str(log)!r}
            case "$1 $2" in
              "pr view") exit 1 ;;
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


def _seed_coga_gitignore(repo) -> None:
    """Give the harness repo the ignore rules a real `coga init` writes.

    `coga launch` rebuilds the merged `coga/.agent-skills/` view on every run.
    A real repo ignores it (see the packaged `coga/.gitignore`); without that,
    an earlier launch into the *primary* checkout leaves it untracked and the
    recipe's clean-tree gate refuses. Only the single-checkout tests notice,
    because they are the ones publishing the checkout they run in.
    """
    (repo.coga_os / ".gitignore").write_text(
        packaged_template_path(".gitignore").read_text()
    )
    repo.git("add", "--", "coga/.gitignore")
    repo.git("commit", "-m", "chore: seed coga-managed ignore rules")


def _feature_worktree(repo, tmp_path: Path, branch: str, *, commit: bool) -> Path:
    wt = tmp_path / f"wt-{branch}"
    repo.git("worktree", "add", str(wt), "-b", branch, "main")
    if commit:
        (wt / "coga" / "change.txt").write_text("a real change\n")
        repo.git("add", "-A", cwd=wt)
        repo.git("commit", "-m", "feature: a real change", cwd=wt)
    return wt


def _write_ticket(coga_os: Path, slug: str, *, branch: str, worktree: Path | None) -> Path:
    task_dir = coga_os / "tasks" / slug
    task_dir.mkdir(parents=True, exist_ok=True)
    dev_lines = [f"branch: {branch}"]
    if worktree is not None:
        dev_lines.append(f"worktree: {worktree}")
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
        "\n## Description\n\nThe change we are shipping.\n\n"
        "<!-- coga:blackboard -->\n\n"
        "## Dev\n"
        f"{chr(10).join(dev_lines)}\n"
    )
    ticket = task_dir / "ticket.md"
    ticket.write_text(frontmatter + body)
    return ticket


# --- tests --------------------------------------------------------------------


def test_open_pr_opens_and_records(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/7")

    wt = _feature_worktree(repo, tmp_path, "feature-x", commit=True)
    ticket = _write_ticket(repo.coga_os, "ship-it", branch="feature-x", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["run", "open-pr", "ship-it"])

    assert result.exit_code == 0, result.output
    assert "pr create" in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) == "https://github.com/acme/repo/pull/7"


def test_open_pr_alias_spelling_end_to_end(tmp_path, monkeypatch):
    """`coga open-pr <slug>` — the default-alias spelling the `code/open-pr`
    step runs — carries the trailing task ref through the argv rewrite into
    the runner's ordinary argv and works end to end."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/8")

    wt = _feature_worktree(repo, tmp_path, "feature-a", commit=True)
    ticket = _write_ticket(repo.coga_os, "by-alias", branch="feature-a", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    monkeypatch.setattr("sys.argv", ["coga", "open-pr", "by-alias"])
    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code in (0, None)
    assert parse_pr_url(read_blackboard(ticket)) == "https://github.com/acme/repo/pull/8"


def test_open_pr_stdout_is_only_the_url(tmp_path, monkeypatch):
    """Moving the verb between spellings must not change what it prints:
    stdout is the value channel, so `$(coga open-pr <slug>)` captures exactly
    the PR URL and nothing else. Diagnostics belong on stderr."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/9")

    wt = _feature_worktree(repo, tmp_path, "feature-q", commit=True)
    ticket = _write_ticket(repo.coga_os, "quiet-out", branch="feature-q", worktree=wt)
    # A stale `pr:` line makes the recipe emit its replacement note, which must
    # not land on the value channel beside the URL.
    ticket.write_text(
        ticket.read_text().replace(
            "## Dev\n", "## Dev\npr: https://github.com/acme/repo/pull/1\n"
        )
    )

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["run", "open-pr", "quiet-out"])

    assert result.exit_code == 0, result.stderr
    assert result.stdout == "https://github.com/acme/repo/pull/9\n"
    # Still visible to a human running it by hand, just off the value channel.
    assert "replaced a stale pr: line" in result.stderr


def test_open_pr_fails_loud_on_no_commits(tmp_path, monkeypatch):
    """The incident case surfaced through the CLI: nothing built → non-zero exit,
    no PR, no recorded `pr:` — so the step's `requires: pr` gate stays unmet."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)

    wt = _feature_worktree(repo, tmp_path, "empty-branch", commit=False)
    ticket = _write_ticket(repo.coga_os, "nothing-built", branch="empty-branch", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["run", "open-pr", "nothing-built"])

    assert result.exit_code == 2, result.output
    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def test_open_pr_unknown_task_fails_loud(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["run", "open-pr", "no-such-task"])
    assert result.exit_code == 2, result.output


def test_open_pr_without_task_arg_fails_with_usage(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["run", "open-pr"])
    assert result.exit_code == 2, result.output


def test_open_pr_refuses_feature_checkout(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    wt = _feature_worktree(repo, tmp_path, "feature-x", commit=True)
    _write_ticket(repo.coga_os, "ship-it", branch="feature-x", worktree=wt)
    (wt / "coga" / "coga.local.toml").write_text('user = "marc"\n')

    monkeypatch.chdir(wt / "coga")
    result = CliRunner().invoke(app, ["run", "open-pr", "ship-it"])

    assert result.exit_code == 2, result.output


def test_open_pr_pushes_recorded_branch_by_name(tmp_path, monkeypatch):
    """The seam the divergence incident lived in: open-pr pushes the branch
    recorded under `## Dev` **by name** while the command remains in the
    control checkout — it never pushes "current HEAD".

    Here the command runs from the control checkout (`coga_os`, sitting on
    `main`), while the feature branch lives in a *separate* worktree — exactly
    the launch-worktree-isolation layout. The recorded branch must still land on
    `origin`, proving it targets the recorded feature worktree rather than the
    command's checkout.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/9")

    wt = _feature_worktree(repo, tmp_path, "detached-feature", commit=True)
    ticket = _write_ticket(
        repo.coga_os, "by-name", branch="detached-feature", worktree=wt
    )

    # The control checkout the command runs from is on `main`, NOT the feature
    # branch — so a "push current HEAD" implementation would push the wrong ref.
    assert repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
    assert not _origin_has_branch(repo, "detached-feature")

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["run", "open-pr", "by-name"])

    assert result.exit_code == 0, result.output
    # The recorded feature branch landed on origin, pointing at the feature commit.
    assert _origin_has_branch(repo, "detached-feature")
    feature_head = repo.git("rev-parse", "detached-feature", cwd=wt).strip()
    origin_head = repo.git("rev-parse", "refs/heads/detached-feature", cwd=repo.origin).strip()
    assert origin_head == feature_head
    assert parse_pr_url(read_blackboard(ticket)) == "https://github.com/acme/repo/pull/9"


def test_open_pr_allows_primary_checkout_feature_branch(
    tmp_path, monkeypatch
):
    """Single-checkout development has no separate control checkout to use.

    Record the primary checkout through a symlink so the seam must compare
    checkout identity rather than raw path strings.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(
        monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/11"
    )

    checkout_alias = tmp_path / "primary-checkout"
    checkout_alias.symlink_to(repo.root, target_is_directory=True)
    ticket = _write_ticket(
        repo.coga_os,
        "single-checkout",
        branch="single-checkout-feature",
        worktree=checkout_alias,
    )
    _seed_coga_gitignore(repo)
    repo.git("add", "--", "coga/tasks/single-checkout/ticket.md")
    repo.git("commit", "-m", "ticket: add single-checkout")
    repo.git("push", "origin", "main")

    repo.checkout_branch("single-checkout-feature")
    (repo.coga_os / "change.txt").write_text("a real change\n")
    repo.git("add", "--", "coga/change.txt")
    repo.git("commit", "-m", "feature: a real change")

    monkeypatch.chdir(repo.coga_os)
    monkeypatch.setenv(EXPECTED_TASK_ENV, str(ticket.parent.resolve()))
    first = CliRunner().invoke(app, ["run", "open-pr", "single-checkout"])
    second = CliRunner().invoke(app, ["run", "open-pr", "single-checkout"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert parse_pr_url(read_blackboard(ticket)) == (
        "https://github.com/acme/repo/pull/11"
    )
    assert repo.git("status", "--porcelain").strip() == ""
    published_ticket = repo.git(
        "show",
        "refs/heads/single-checkout-feature:coga/tasks/single-checkout/ticket.md",
        cwd=repo.origin,
    )
    assert "pr: https://github.com/acme/repo/pull/11" in published_ticket


def test_single_checkout_open_pr_bump_republishes_final_ticket_state(
    tmp_path, monkeypatch, real_git
):
    """The required bump must not leave a conflicting stale ticket in the PR."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(
        monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/15"
    )

    branch = "single-checkout-final-state"
    slug = "single-checkout-final-state"
    ticket = _write_ticket(repo.coga_os, slug, branch=branch, worktree=repo.root)
    ticket.write_text(
        ticket.read_text().replace(
            "    - name: open-pr\n",
            "    - name: open-pr\n      requires: pr\n",
        )
    )
    _seed_coga_gitignore(repo)
    ticket_rel = f"coga/tasks/{slug}/ticket.md"
    repo.git("add", "--", ticket_rel)
    repo.git("commit", "-m", "ticket: seed single-checkout workflow")
    repo.git("push", "origin", "main")

    repo.checkout_branch(branch)
    (repo.root / "implementation.txt").write_text("publishable work\n")
    repo.git("add", "--", "implementation.txt")
    repo.git("commit", "-m", "feature: add publishable work")

    monkeypatch.chdir(repo.coga_os)
    monkeypatch.setenv(EXPECTED_TASK_ENV, str(ticket.parent.resolve()))
    opened = CliRunner().invoke(app, ["run", "open-pr", slug])
    assert opened.exit_code == 0, opened.output

    bumped = CliRunner().invoke(app, ["bump", slug])
    assert bumped.exit_code == 0, bumped.output

    control_ticket = repo.git(
        "show", f"refs/heads/main:{ticket_rel}", cwd=repo.origin
    )
    feature_ticket = repo.git(
        "show", f"refs/heads/{branch}:{ticket_rel}", cwd=repo.origin
    )
    assert feature_ticket == control_ticket
    assert "step: 2 (review)" in feature_ticket
    assert "pr: https://github.com/acme/repo/pull/15" in feature_ticket
    assert repo.git("rev-parse", "HEAD").strip() == repo.git(
        "rev-parse", f"refs/heads/{branch}", cwd=repo.origin
    ).strip()


def test_open_pr_refuses_independent_feature_clone(tmp_path, monkeypatch):
    """An inherited launch anchor keeps a fallback clone non-authoritative."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    clone = tmp_path / "feature-clone"

    ticket = _write_ticket(
        repo.coga_os, "clone-task", branch="clone-feature", worktree=clone
    )
    repo.git("add", "--", "coga/tasks/clone-task/ticket.md")
    repo.git("commit", "-m", "ticket: add clone-task")
    repo.git("push", "origin", "main")

    repo.git("clone", "--no-hardlinks", str(repo.root), str(clone), cwd=tmp_path)
    repo.git("config", "user.email", "clone@example.com", cwd=clone)
    repo.git("config", "user.name", "Clone", cwd=clone)
    repo.git("config", "commit.gpgsign", "false", cwd=clone)
    repo.git("remote", "set-url", "origin", str(repo.origin), cwd=clone)
    (clone / "coga" / "coga.local.toml").write_text('user = "marc"\n')
    repo.git("checkout", "-b", "clone-feature", cwd=clone)
    (clone / "coga" / "change.txt").write_text("a real change\n")
    repo.git("add", "--", "coga/change.txt", cwd=clone)
    repo.git("commit", "-m", "feature: a real change", cwd=clone)

    # The anchor names the *primary* checkout's task, so the clone's identical
    # copy at a different path cannot match it and stays non-authoritative.
    monkeypatch.setenv(EXPECTED_TASK_ENV, str(ticket.parent.resolve()))
    monkeypatch.chdir(clone / "coga")
    result = CliRunner().invoke(app, ["run", "open-pr", "clone-task"])

    assert result.exit_code == 2, result.output
    assert (
        "cannot prove that this feature checkout owns the live ticket"
        in result.stderr
    )
    assert not log.exists() or "pr create" not in log.read_text()
    assert (
        parse_pr_url(
            read_blackboard(clone / "coga" / "tasks" / "clone-task" / "ticket.md")
        )
        is None
    )


def test_open_pr_ships_as_a_registered_recipe() -> None:
    """open-pr is a fixed name in the runner's table, so its implementation is
    importable core — and the retired command-ticket seam ships nothing."""
    assert RECIPES["open-pr"] is run_open_pr_recipe
    src_root = Path(coga.__file__).resolve().parent
    assert (src_root / "open_pr.py").is_file()
    assert not packaged_template_path("bootstrap").joinpath("open-pr").exists()


def _origin_has_branch(repo, branch: str) -> bool:
    out = repo.git("branch", "--list", branch, cwd=repo.origin)
    return bool(out.strip())
