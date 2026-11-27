from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml
from typer.testing import CliRunner

from coga.blackboard import read_dev_fields, set_dev_fields
from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.task_env import build_task_env, SCRIPT_TASK_ENV
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import read_ticket, resolve_task


_SKILLS = Path(__file__).resolve().parents[1] / "src/coga/resources/templates/coga/bootstrap/skills"
_PR_URL = "https://github.com/example/repo/pull/7"


def _script(ref):
    spec = importlib.util.spec_from_file_location("workflow_script", _SKILLS / ref / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def git_ticket(git_repo, monkeypatch):
    with (git_repo.coga_os / "coga.local.toml").open("a", encoding="utf-8") as stream:
        stream.write("\n[notification.slack]\nenabled = false\n")
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg, title="Git workflow", workflow_name="direct/body", contexts=[],
        owner=cfg.current_user, agent=cfg.default_agent().name, status="active",
    )
    ref = resolve_task(cfg, created["slug"])
    ticket = read_ticket(ref)
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    for key, value in build_task_env(cfg, ref, ticket).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv(SCRIPT_TASK_ENV, str(ref.path.resolve()))
    git_repo.git("add", "coga")
    git_repo.git("commit", "-m", "Seed workflow ticket")
    git_repo.git("push", "origin", "main")
    return git_repo, ref


def _dev(ref, **fields):
    replace_blackboard(ref.ticket_path, set_dev_fields(read_blackboard(ref.ticket_path), **fields))


def test_open_branch_creates_and_backfills_without_bumping(git_ticket, monkeypatch):
    repo, ref = git_ticket
    script = _script("git/open-branch")
    monkeypatch.setattr(sys, "argv", ["run.py", "--no-bump"])
    assert script.main() == 0
    first = read_dev_fields(read_blackboard(ref.ticket_path))
    assert first == {"branch": repo.git("branch", "--show-current").strip(), "base": "main", "remote": "origin"}
    assert read_ticket(ref).step == "1 (execute)"

    repo.git("switch", "main")
    replace_blackboard(ref.ticket_path, set_dev_fields("\n", branch=first["branch"]))
    monkeypatch.setattr(sys, "argv", ["run.py", "--no-bump", "--base", "main"])
    assert script.main() == 0
    assert read_dev_fields(read_blackboard(ref.ticket_path)) == first


def test_open_branch_git_error_does_not_bump(git_ticket, monkeypatch):
    repo, ref = git_ticket
    _dev(ref, branch="missing", base="main", remote="origin")
    monkeypatch.setattr(sys, "argv", ["run.py"])
    assert _script("git/open-branch").main() != 0
    assert repo.git("branch", "--show-current").strip() == "main"
    assert read_ticket(ref).step == "1 (execute)"


@pytest.mark.parametrize("mode", ["create", "reuse", "draft", "closed", "wrong-base", "retry", "retry-create", "stale"])
def test_push_and_open_pr(git_ticket, monkeypatch, mode):
    repo, ref = git_ticket
    repo.git("switch", "-c", "work")
    _dev(ref, branch="work", base="main", remote="origin")
    base = repo.git("rev-parse", "main").strip()
    source = repo.root / "change.txt"
    source.write_text("reviewed change", encoding="utf-8")
    repo.git("add", "change.txt")
    repo.git("commit", "-m", "Implement reviewed change")
    head = repo.git("rev-parse", "HEAD").strip()
    receipt = {"head": head, "base": base, "status": "passed", "detail": "Verified."}
    preparation = {
        "head": head, "base": base, "author": "codex", "author_evidence": "Implement session.",
        "title": "Add a change", "depth": "skim", "rationale": "Bounded change.",
        "implementation": "Add change.txt.", "deviations": "None.", "limitations": "None.",
        "files": {"change.txt": "The implementation."},
        "review": {**receipt, "kind": "independent", "reviewer": "claude"},
        "checks": [{**receipt, "command": "pytest"}],
    }
    replace_blackboard(
        ref.ticket_path, read_blackboard(ref.ticket_path).rstrip()
        + "\n\n## PR\n\n```yaml\n" + yaml.safe_dump(preparation) + "```\n",
    )
    if mode == "stale":
        source.write_text("unreviewed change", encoding="utf-8")
        repo.git("commit", "-m", "Change reviewed file", "--", "change.txt")
        source.write_text("reviewed change", encoding="utf-8")
        repo.git("commit", "-m", "Restore reviewed file", "--", "change.txt")
    other_ticket = repo.coga_os / "tasks" / "other-ticket.md"
    if mode == "create":
        # Another ticket's uncommitted edit in the shared checkout.
        other_ticket.write_text("---\ntitle: Other\n---\n", encoding="utf-8")
    script = _script("git/push-and-open-pr")
    real_run = subprocess.run
    real_output = subprocess.check_output
    calls = []
    exists = mode not in {"create", "retry", "retry-create", "stale"}
    fail_push = mode == "retry"
    actual_pushes = 0

    def run(args, *positional, **kwargs):
        nonlocal actual_pushes, fail_push
        if args[:3] == ["gh", "pr", "view"]:
            calls.append("view")
            if not exists:
                return subprocess.CompletedProcess(args, 1, "", 'no pull requests found for branch "work"')
            data = dict(url=_PR_URL, state="CLOSED" if mode == "closed" else "OPEN",
                        baseRefName="other" if mode == "wrong-base" else "main",
                        isDraft=mode == "draft")
            return subprocess.CompletedProcess(args, 0, json.dumps(data), "")
        if args[:3] == ["gh", "pr", "ready"]:
            calls.append("ready")
            return subprocess.CompletedProcess(args, 0)
        if args[:2] == ["git", "push"]:
            actual_pushes += 1
            if fail_push and actual_pushes == 1:
                fail_push = False
                raise subprocess.CalledProcessError(1, args)
        return real_run(args, *positional, **kwargs)

    def output(args, *positional, **kwargs):
        nonlocal exists
        if args[:3] == ["gh", "pr", "create"]:
            calls.append("create")
            if mode == "retry-create" and calls.count("create") == 1:
                raise subprocess.CalledProcessError(1, args)
            exists = True
            body = Path(args[args.index("--body-file") + 1]).read_text(encoding="utf-8")
            assert "## Checks" in body
            # Ticket state never rides the code branch.
            assert ref.ticket_path.relative_to(repo.root).as_posix() not in body
            assert "Unexplained path:" not in body
            if mode == "stale":
                assert "Stale preparation:" in body
                assert "**stale**" in body
            else:
                assert "Publication evidence gaps:" not in body
                assert "**passed**" in body
            return _PR_URL + "\n"
        return real_output(args, *positional, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "check_output", output)
    if mode in {"closed", "wrong-base"}:
        assert script.main() != 0
        assert read_ticket(ref).step == "1 (execute)"
        return
    if mode == "retry":
        assert script.main() == 1
        assert read_ticket(ref).step == "1 (execute)"
    if mode == "retry-create":
        assert script.main() == 1
        assert read_ticket(ref).step == "1 (execute)"
    assert script.main() == 0
    assert read_dev_fields(read_blackboard(ref.ticket_path))["pr"] == _PR_URL
    assert read_ticket(ref).status == "done"
    assert calls.count("create") == (2 if mode == "retry-create" else int(mode in {"create", "retry", "stale"}))
    assert ("ready" in calls) == (mode == "draft")
    assert repo.git("rev-parse", "HEAD").strip() == repo.git("rev-parse", "work", cwd=repo.origin).strip()
    if mode == "create":
        # It neither blocked the PR nor rode along on the branch.
        assert other_ticket.is_file()
        assert "other-ticket.md" not in repo.git("ls-tree", "-r", "--name-only", "work", cwd=repo.origin)


@pytest.mark.parametrize("condition, message", [
    ("missing", "Missing ## Dev fields"),
    ("mismatch", "disagrees with recorded branch"),
    ("dirty", "Commit your work first"),
])
def test_pr_script_refuses_before_mutating(git_ticket, condition, message, capsys):
    repo, ref = git_ticket
    if condition != "missing":
        _dev(ref, branch="other" if condition == "mismatch" else "main", base="base", remote="origin")
    if condition == "dirty":
        (repo.root / "dirty.txt").write_text("local edit", encoding="utf-8")
    head = repo.git("rev-parse", "HEAD")
    assert _script("git/push-and-open-pr").main() == 2
    assert message in capsys.readouterr().err
    assert repo.git("rev-parse", "HEAD") == head


def test_merge_script_checks_every_post_review_commit(git_ticket):
    repo, ref = git_ticket
    repo.git("switch", "-c", "work")
    script = _script("code/merge-pr")
    reviewed = repo.git("rev-parse", "HEAD").strip()
    _dev(ref, reviewed=reviewed)
    ticket = ref.ticket_path.relative_to(repo.root).as_posix()
    repo.git("commit", "--only", "-m", "Record review", "--", ticket)
    script.verify_reviewed_tree(str(repo.root), reviewed, repo.git("rev-parse", "HEAD").strip(), (ticket, "coga/log.md"))
    path = repo.root / "extra.txt"
    path.write_text("change", encoding="utf-8")
    repo.git("add", "extra.txt")
    repo.git("commit", "-m", "Unreviewed change")
    repo.git("rm", "extra.txt")
    repo.git("commit", "-m", "Restore reviewed tree")
    with pytest.raises(ValueError, match="extra.txt"):
        script.verify_reviewed_tree(str(repo.root), reviewed, repo.git("rev-parse", "HEAD").strip(), (ticket, "coga/log.md"))


def test_bump_changes_local_ticket_and_log_without_committing(git_ticket):
    repo, ref = git_ticket
    original_head = repo.git("rev-parse", "HEAD")
    result = CliRunner().invoke(app, ["bump", ref.id_slug])
    assert result.exit_code == 0, result.output
    assert read_ticket(ref).status == "done"
    assert repo.git("rev-parse", "HEAD") == original_head
    changed = {line[3:] for line in repo.git("status", "--porcelain").splitlines()}
    assert changed == {ref.ticket_path.relative_to(repo.root).as_posix(), "coga/log.md"}


def test_legacy_implement_dispatch_stays_on_its_step(git_ticket, monkeypatch):
    from coga import launch as launch_module
    from coga.repl_supervisor import ReplOutcome

    repo, ref = git_ticket
    ticket = read_ticket(ref)
    ticket.frontmatter["workflow"] = {
        "name": "code/with-review",
        "steps": [{
            "name": "implement", "skills": ["code/implement"], "assignee": "agent",
            "checkout": "create-or-reuse", "requires": "branch",
        }],
    }
    ticket.frontmatter["step"] = "1 (implement)"
    ticket.write(ref.ticket_path)
    repo.git("add", "coga")
    repo.git("commit", "-m", "Seed legacy snapshot")
    monkeypatch.setattr(launch_module, "interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(launch_module.shutil, "which", lambda name: name)

    def implement(cmd, env, **kwargs):
        subprocess.run(
            [sys.executable, str(_SKILLS / "git/open-branch/run.py"), "--no-bump"],
            env=env, check=True,
        )
        return ReplOutcome(0, "natural")

    monkeypatch.setattr(launch_module, "run_with_done_marker", implement)
    result = CliRunner().invoke(app, ["launch", ref.id_slug])
    assert result.exit_code == 0, result.output
    assert read_ticket(ref).step == "1 (implement)"
    branch = read_dev_fields(read_blackboard(ref.ticket_path))["branch"]
    assert repo.git("branch", "--show-current").strip() == branch


def test_merge_script_merges_the_reviewed_head_then_finishes(git_ticket, monkeypatch):
    repo, ref = git_ticket
    repo.git("switch", "-c", "work")
    reviewed = repo.git("rev-parse", "HEAD").strip()
    _dev(ref, branch="work", base="main", remote="origin", reviewed=reviewed, pr=_PR_URL)
    script = _script("code/merge-pr")
    run_command = subprocess.run
    output_command = subprocess.check_output
    calls = []

    def output(argv, *args, **kwargs):
        if argv[:3] == ["gh", "pr", "view"]:
            calls.append("view")
            head = repo.git("rev-parse", "work", cwd=repo.origin).strip()
            assert head == reviewed
            assert read_ticket(ref).status != "done"
            return json.dumps({
                "state": "OPEN", "isDraft": False, "baseRefName": "main",
                "headRefOid": head, "statusCheckRollup": [{}],
            })
        if argv[:3] == ["gh", "repo", "view"]:
            calls.append("method")
            return json.dumps({"viewerDefaultMergeMethod": "REBASE", "rebaseMergeAllowed": True})
        return output_command(argv, *args, **kwargs)

    def run(argv, *args, **kwargs):
        if argv[:3] == ["gh", "pr", "checks"]:
            calls.append("checks")
            assert argv[3:] == [_PR_URL, "--watch", "--fail-fast"]
            return subprocess.CompletedProcess(argv, 0)
        if argv[:3] == ["gh", "pr", "merge"]:
            calls.append("merge")
            head = repo.git("rev-parse", "work", cwd=repo.origin).strip()
            assert argv[3:] == [_PR_URL, "--rebase", "--match-head-commit", head]
            return subprocess.CompletedProcess(argv, 0)
        if "bump" in argv:
            calls.append("bump")
        return run_command(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", output)
    monkeypatch.setattr(subprocess, "run", run)
    assert script.main() == 0
    # The final bump (which runs the workflow's exit script) comes last.
    assert calls == ["view", "checks", "method", "merge", "bump"]
    assert read_ticket(ref).status == "done"
