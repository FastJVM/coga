"""Tests for the `coga open-pr` command seam — now the `bootstrap/open-pr`
command ticket, launched statelessly with the target task ref on the launch
arg channel (`coga open-pr <slug>` is a default alias for
`coga launch bootstrap/open-pr <slug>`).

The recipe itself is covered by `test_open_pr.py`; here we exercise the seam:
the launch dispatch runs the ticket's `run.py` as a stateless script, which
resolves the task from `COGA_ARG_1`, runs the recipe, prints the URL, and maps
an `OpenPrError` (or a wrong-checkout refusal) to a non-zero exit. The headline
case is the one the original ticket calls out explicitly — pushing the recorded
`## Dev` branch **by name** is agnostic to which feature worktree holds it. The
command itself stays on the primary control checkout so task resolution and the
blackboard write are authoritative.

Mirrors `test_open_pr.py`'s real-git harness (a bare `origin` + a fake `gh` on
PATH) so push/PR behaviour is exercised for real without a network. The
`run.py` child imports `coga` in a `sys.executable` subprocess, so each test
exports the parent's import path as `PYTHONPATH` (same hermeticity note as
`test_launch_script.py`'s bootstrap test).
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
from coga.paths import packaged_template_path
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


def _export_child_import_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let the `run.py` subprocess import `coga` from the parent's source tree."""
    monkeypatch.setenv(
        "PYTHONPATH", str(Path(coga.__file__).resolve().parents[1])
    )


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


def test_open_pr_launch_opens_and_records(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/7")
    _export_child_import_path(monkeypatch)

    wt = _feature_worktree(repo, tmp_path, "feature-x", commit=True)
    ticket = _write_ticket(repo.coga_os, "ship-it", branch="feature-x", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["launch", "bootstrap/open-pr", "ship-it"])

    assert result.exit_code == 0, result.output
    assert "pr create" in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) == "https://github.com/acme/repo/pull/7"


def test_open_pr_alias_spelling_end_to_end(tmp_path, monkeypatch):
    """`coga open-pr <slug>` — the default-alias spelling the `code/open-pr`
    step runs — carries the trailing task ref through the argv rewrite into
    `COGA_ARG_1` and works end to end."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/8")
    _export_child_import_path(monkeypatch)

    wt = _feature_worktree(repo, tmp_path, "feature-a", commit=True)
    ticket = _write_ticket(repo.coga_os, "by-alias", branch="feature-a", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    monkeypatch.setattr("sys.argv", ["coga", "open-pr", "by-alias"])
    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code in (0, None)
    assert parse_pr_url(read_blackboard(ticket)) == "https://github.com/acme/repo/pull/8"


def test_open_pr_launch_stdout_is_only_the_url(tmp_path, monkeypatch, capfd):
    """Moving a verb behind a command ticket must not change what the verb
    prints. `coga open-pr <slug>` printed exactly the PR URL on stdout before
    the move, so the launcher's own framing ("Launch: task ...", "script ran
    successfully") belongs on stderr — otherwise `$(coga open-pr <slug>)`
    captures unparsable output even though the PR was created.

    The script is a real child process, so its URL lands on the *file
    descriptor* (read here with `capfd`) while the launcher's own echoes go
    through `sys.stdout` / `sys.stderr` (read from the runner result). Both
    are one stream at a terminal; the assertion is that the launcher puts
    nothing on the value channel."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/9")
    _export_child_import_path(monkeypatch)

    wt = _feature_worktree(repo, tmp_path, "feature-q", commit=True)
    _write_ticket(repo.coga_os, "quiet-out", branch="feature-q", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["launch", "bootstrap/open-pr", "quiet-out"])

    assert result.exit_code == 0, result.stderr
    assert result.stdout.strip() == ""
    # Still visible to a human running it by hand, just off the value channel.
    assert "Launch: task bootstrap/open-pr" in result.stderr
    assert "script ran successfully" in result.stderr
    assert capfd.readouterr().out.strip() == "https://github.com/acme/repo/pull/9"


def test_open_pr_launch_fails_loud_on_no_commits(tmp_path, monkeypatch):
    """The incident case surfaced through the CLI: nothing built → non-zero exit,
    no PR, no recorded `pr:` — and the stateless launch advances nothing."""
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _install_fake_gh(monkeypatch, bin_dir)
    _export_child_import_path(monkeypatch)

    wt = _feature_worktree(repo, tmp_path, "empty-branch", commit=False)
    ticket = _write_ticket(repo.coga_os, "nothing-built", branch="empty-branch", worktree=wt)

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["launch", "bootstrap/open-pr", "nothing-built"])

    assert result.exit_code == 2, result.output
    assert not log.exists() or "pr create" not in log.read_text()
    assert parse_pr_url(read_blackboard(ticket)) is None


def test_open_pr_launch_unknown_task_fails_loud(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    _export_child_import_path(monkeypatch)
    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["launch", "bootstrap/open-pr", "no-such-task"])
    assert result.exit_code == 2, result.output


def test_open_pr_launch_without_task_arg_fails_with_usage(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    _export_child_import_path(monkeypatch)
    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["launch", "bootstrap/open-pr"])
    assert result.exit_code == 2, result.output


def test_open_pr_launch_refuses_feature_checkout(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path)
    _export_child_import_path(monkeypatch)
    wt = _feature_worktree(repo, tmp_path, "feature-x", commit=True)
    _write_ticket(repo.coga_os, "ship-it", branch="feature-x", worktree=wt)
    (wt / "coga" / "coga.local.toml").write_text('user = "marc"\n')

    monkeypatch.chdir(wt / "coga")
    result = CliRunner().invoke(app, ["launch", "bootstrap/open-pr", "ship-it"])

    assert result.exit_code == 2, result.output


def test_open_pr_launch_pushes_recorded_branch_by_name(tmp_path, monkeypatch):
    """The seam the divergence incident lived in: open-pr pushes the branch
    recorded under `## Dev` **by name** while the command remains in the
    control checkout — it never pushes "current HEAD".

    Here the launch runs from the control checkout (`coga_os`, sitting on
    `main`), while the feature branch lives in a *separate* worktree — exactly
    the launch-worktree-isolation layout. The recorded branch must still land on
    `origin`, proving it targets the recorded feature worktree rather than the
    command's checkout.
    """
    repo = init_git_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_gh(monkeypatch, bin_dir, create_url="https://github.com/acme/repo/pull/9")
    _export_child_import_path(monkeypatch)

    wt = _feature_worktree(repo, tmp_path, "detached-feature", commit=True)
    ticket = _write_ticket(
        repo.coga_os, "by-name", branch="detached-feature", worktree=wt
    )

    # The control checkout the command runs from is on `main`, NOT the feature
    # branch — so a "push current HEAD" implementation would push the wrong ref.
    assert repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
    assert not _origin_has_branch(repo, "detached-feature")

    monkeypatch.chdir(repo.coga_os)
    result = CliRunner().invoke(app, ["launch", "bootstrap/open-pr", "by-name"])

    assert result.exit_code == 0, result.output
    # The recorded feature branch landed on origin, pointing at the feature commit.
    assert _origin_has_branch(repo, "detached-feature")
    feature_head = repo.git("rev-parse", "detached-feature", cwd=wt).strip()
    origin_head = repo.git("rev-parse", "refs/heads/detached-feature", cwd=repo.origin).strip()
    assert origin_head == feature_head
    assert parse_pr_url(read_blackboard(ticket)) == "https://github.com/acme/repo/pull/9"


def test_open_pr_ships_as_a_command_ticket() -> None:
    """The packaged `bootstrap/open-pr` dir is a complete command ticket:
    ticket definition + script seam + recipe, and nothing left in core."""
    packaged = packaged_template_path("bootstrap", "open-pr")
    assert (packaged / "ticket.md").is_file()
    assert (packaged / "run.py").is_file()
    assert (packaged / "recipe.py").is_file()
    src_root = Path(coga.__file__).resolve().parent
    assert not (src_root / "open_pr.py").exists()
    assert not (src_root / "commands" / "open_pr.py").exists()


def _origin_has_branch(repo, branch: str) -> bool:
    out = repo.git("branch", "--list", branch, cwd=repo.origin)
    return bool(out.strip())
