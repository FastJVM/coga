"""`git: ticket-branch` launch mode against a real repo and a local bare remote."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import coga.launch as launch_module
from coga.blackboard import read_dev_fields, set_dev_fields
from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.launch import LaunchBail, launch
from coga.repl_supervisor import ReplOutcome, _TIMEOUT_EXIT_CODE
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import read_ticket, resolve_task
from coga.ticket import Ticket

_SKILLS = Path(__file__).resolve().parents[1] / "src/coga/resources/templates/coga/bootstrap/skills"
_HOOK = _SKILLS / "git/ticket-branch/run.py"

WORKFLOW = """---
name: tb
description: Ticket-branch test workflow.
git: ticket-branch
steps:
  - name: design
    assignee: agent
  - name: review-design
    assignee: owner
  - name: open-branch
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    assignee: agent
  - name: review
    assignee: owner
---

## design
Design it.

## review-design
Review the design.

## implement
Implement it.

## review
Review it.
"""


@pytest.fixture
def tb(git_repo, monkeypatch):
    repo = git_repo
    with (repo.root / ".gitignore").open("a", encoding="utf-8") as stream:
        stream.write("coga/.coga/\n")
    with (repo.coga_os / "coga.local.toml").open("a", encoding="utf-8") as stream:
        stream.write("\n[notification.slack]\nenabled = false\n")
    (repo.coga_os / "workflows" / "tb.md").write_text(WORKFLOW, encoding="utf-8")
    (repo.coga_os / "workflows" / "plain.md").write_text(
        WORKFLOW.replace("git: ticket-branch\n", ""), encoding="utf-8"
    )
    cfg = load_config(repo.coga_os)
    created = create_task(
        cfg=cfg, title="Branch work", workflow_name="tb", contexts=[],
        owner=cfg.current_user, agent=cfg.default_agent().name, status="active",
    )
    ref = resolve_task(cfg, created["slug"])
    repo.git("add", "-A")
    repo.git("commit", "-m", "Seed ticket-branch ticket")
    repo.git("push", "origin", "main")
    for key in [k for k in os.environ if k.startswith("COGA_") and k != "COGA_SYSTEM_TMPDIR"]:
        monkeypatch.delenv(key)
    monkeypatch.setattr(launch_module, "interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(launch_module.shutil, "which", lambda name, **kwargs: f"/usr/bin/{name}")
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", lambda **kwargs: None)
    return repo, ref


def _agent(monkeypatch, action):
    """Install a fake agent session; `action(env)` may return a ReplOutcome."""
    seen: list[dict] = []

    def fake(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(dict(env))
        outcome = action(env)
        return outcome if isinstance(outcome, ReplOutcome) else ReplOutcome(0, "natural")

    monkeypatch.setattr(launch_module, "run_with_done_marker", fake)
    return seen


def _bump(slug: str) -> None:
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output


def _branch(repo) -> str:
    return repo.git("branch", "--show-current").strip()


def _show(repo, ref_name: str, ref) -> Ticket:
    rel = ref.ticket_path.resolve().relative_to(repo.root.resolve()).as_posix()
    return Ticket.parse(repo.git("show", f"{ref_name}:{rel}"))


def _remote_branches(repo) -> set[str]:
    out = repo.git("--git-dir", str(repo.origin), "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    return set(out.split())


def _dirty(repo) -> str:
    return repo.git("status", "--porcelain", "--untracked-files=all")


def _first_launch(repo, ref, monkeypatch) -> str:
    """Run `design` from main; return the created branch."""
    observed: dict = {}

    def design(env):
        observed["branch"] = _branch(repo)
        observed["dev"] = read_dev_fields(read_blackboard(ref.ticket_path))
        _bump(ref.id_slug)

    _agent(monkeypatch, design)
    assert launch(ref.id_slug).exit_code == 0
    assert observed["dev"] == {"branch": observed["branch"], "base": "main", "remote": "origin"}
    return observed["branch"]


# --- workflow field ------------------------------------------------------------


def test_workflow_git_field_parses_freezes_and_rejects(tmp_path):
    from coga.workflow import Workflow, WorkflowError

    path = tmp_path / "w.md"
    path.write_text(WORKFLOW, encoding="utf-8")
    wf = Workflow.load(path)
    assert wf.git == "ticket-branch"
    frozen = wf.freeze()
    assert list(frozen) == ["name", "git", "steps"]

    for text in (WORKFLOW.replace("git: ticket-branch\n", ""), WORKFLOW.replace("ticket-branch", "main", 1)):
        path.write_text(text, encoding="utf-8")
        wf = Workflow.load(path)
        assert wf.git == "main"
        assert list(wf.freeze()) == ["name", "steps"]

    path.write_text(WORKFLOW.replace("git: ticket-branch", "git: trunk"), encoding="utf-8")
    with pytest.raises(WorkflowError) as exc:
        Workflow.load(path)
    assert str(path) in str(exc.value) and "ticket-branch" in str(exc.value)


def test_git_mode_reads_frozen_and_draft_references(tb):
    from coga.workflow import WorkflowError, git_mode

    repo, _ = tb
    cfg = load_config(repo.coga_os)
    assert git_mode(None, cfg) == "main"
    assert git_mode({"name": "x", "steps": []}, cfg) == "main"
    assert git_mode({"name": "x", "git": "ticket-branch", "steps": []}, cfg) == "ticket-branch"
    assert git_mode("tb", cfg) == "ticket-branch"
    assert git_mode("plain", cfg) == "main"
    with pytest.raises(WorkflowError):
        git_mode({"name": "x", "git": "bogus", "steps": []}, cfg)


def test_validate_reports_unknown_frozen_git_mode(tb):
    from coga.validate import run as validate_run

    repo, ref = tb
    ticket = read_ticket(ref)
    ticket.frontmatter["workflow"]["git"] = "trunk"
    ticket.write(ref.ticket_path)
    issues = [
        issue for issue in validate_run(load_config(repo.coga_os)).issues
        if issue.kind == "bad-shape" and "workflow.git" in issue.message
    ]
    assert issues and issues[0].severity == "error"


# --- launch scenarios ----------------------------------------------------------


def test_first_launch_creates_branch_records_dev_and_returns_to_main(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    assert branch.startswith("coga/")
    assert _branch(repo) == "main"
    assert _dirty(repo) == ""
    assert branch in _remote_branches(repo)
    on_branch = _show(repo, f"origin/{branch}", ref)
    assert on_branch.step == "2 (review-design)"
    assert read_dev_fields(on_branch.body) == {"branch": branch, "base": "main", "remote": "origin"}
    subject = repo.git("log", "-1", "--format=%s", branch).strip()
    assert subject == f"{ref.id_slug}: launch handoff at review-design"
    # main keeps its stale copy; the live ticket lives on the branch.
    assert read_ticket(ref).step == "1 (design)"
    assert repo.git("rev-parse", branch).strip() == repo.git("rev-parse", f"origin/{branch}").strip()


def test_end_to_end_design_assist_open_branch_implement_from_main(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)

    steps: list[tuple[str, str]] = []

    def work(env):
        current = read_ticket(ref)
        steps.append((_branch(repo), current.step))
        if current.step == "4 (implement)":
            (repo.root / "feature.txt").write_text("done\n", encoding="utf-8")
        _bump(ref.id_slug)

    _agent(monkeypatch, work)
    # Owner review-design through an assist, launched from main.
    assert _branch(repo) == "main"
    assert launch(ref.id_slug, agent_override="claude").exit_code == 0
    assert _branch(repo) == "main"
    live = _show(repo, branch, ref)
    if live.step == "3 (open-branch)":
        # The assist hands back after its one session; resume from main.
        assert launch(ref.id_slug).exit_code == 0
        assert _branch(repo) == "main"
        live = _show(repo, branch, ref)
    assert live.step == "5 (review)"
    assert all(where == branch for where, _ in steps)
    assert [step for _, step in steps][0] == "2 (review-design)"
    assert "4 (implement)" in [step for _, step in steps]
    assert read_dev_fields(live.body) == {"branch": branch, "base": "main", "remote": "origin"}
    assert repo.git("show", f"origin/{branch}:feature.txt") == "done\n"
    assert _dirty(repo) == ""


def test_resume_runs_branch_step_not_stale_main_copy(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    # Advance the branch copy past the owner gate by hand.
    repo.git("switch", branch)
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "4 (implement)"
    ticket.write(ref.ticket_path)
    repo.git("commit", "-qam", "advance")
    repo.git("switch", "main")
    assert read_ticket(ref).step == "1 (design)"  # stale main copy, committed

    seen = _agent(monkeypatch, lambda env: _bump(ref.id_slug))
    assert launch(ref.id_slug).exit_code == 0
    assert seen[0]["COGA_TASK_STEP"] == "4 (implement)"
    assert _show(repo, branch, ref).step == "5 (review)"
    assert _branch(repo) == "main"


def test_resume_finds_older_random_suffix_branch(tb, monkeypatch):
    repo, ref = tb
    from coga_edge.git_workflow import branch_slug_part

    old = f"coga/{branch_slug_part(ref.id_slug)}-abc123"
    repo.git("switch", "-c", old)
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "4 (implement)"
    ticket.write(ref.ticket_path)
    replace_blackboard(
        ref.ticket_path,
        set_dev_fields(read_blackboard(ref.ticket_path), branch=old, base="main", remote="origin"),
    )
    repo.git("commit", "-qam", "old branch")
    repo.git("switch", "main")

    seen = _agent(monkeypatch, lambda env: (_bump(ref.id_slug), None)[1])
    assert launch(ref.id_slug).exit_code == 0
    assert seen[0]["COGA_TASK_STEP"] == "4 (implement)"
    assert old in _remote_branches(repo)
    assert _show(repo, old, ref).step == "5 (review)"


def test_main_mode_runs_no_hook(tb, monkeypatch):
    repo, ref = tb
    ticket = read_ticket(ref)
    del ticket.frontmatter["workflow"]["git"]
    ticket.write(ref.ticket_path)
    repo.git("commit", "-qam", "main mode")

    def no_hook(*args, **kwargs):
        raise AssertionError("main mode must not run a launch hook")

    monkeypatch.setattr(launch_module, "run_launch_hook", no_hook)
    _agent(monkeypatch, lambda env: _bump(ref.id_slug))
    assert launch(ref.id_slug).exit_code == 0
    assert _branch(repo) == "main"
    assert read_ticket(ref).step == "2 (review-design)"


def test_prompt_report_runs_no_hook(tb, monkeypatch):
    _, ref = tb

    def no_hook(*args, **kwargs):
        raise AssertionError("--prompt-report must not run a launch hook")

    monkeypatch.setattr(launch_module, "run_launch_hook", no_hook)
    assert launch(ref.id_slug, prompt_report=True).exit_code == 0


def test_mode_mismatch_after_enter_bails_and_still_exits(tb, monkeypatch, capfd):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("switch", branch)
    ticket = read_ticket(ref)
    del ticket.frontmatter["workflow"]["git"]
    ticket.write(ref.ticket_path)
    repo.git("commit", "-qam", "drop mode on branch")
    repo.git("switch", "main")
    _agent(monkeypatch, lambda env: pytest.fail("no agent after a mode mismatch"))
    with pytest.raises(LaunchBail) as exc:
        launch(ref.id_slug)
    assert "git: ticket-branch" in exc.value.reason and "git: main" in exc.value.reason
    assert _branch(repo) == "main"


def test_enter_does_not_substitute_another_ticket_matching_the_prefix(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("switch", branch)
    repo.git("mv", str(ref.ticket_path), str(ref.ticket_path.with_stem(ref.slug + "-other")))
    repo.git("commit", "-qm", "Rename the ticket on its branch")
    repo.git("switch", "main")
    replace_blackboard(
        ref.ticket_path, set_dev_fields(read_blackboard(ref.ticket_path),
                                       branch=branch, base="main", remote="origin"),
    )
    repo.git("commit", "-qam", "Record the branch on main")
    _agent(monkeypatch, lambda env: pytest.fail("no agent for the other ticket"))
    with pytest.raises(LaunchBail, match="missing after enter"):
        launch(ref.id_slug)
    assert _branch(repo) == "main"


def test_terminal_ticket_refusal_still_publishes_checkout(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("switch", branch)
    ticket = read_ticket(ref)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(ref.ticket_path)
    # Leave the change uncommitted and launch from the ticket branch itself.
    with pytest.raises(LaunchBail) as exc:
        launch(ref.id_slug)
    assert "terminal" in exc.value.reason
    assert _branch(repo) == branch
    assert _dirty(repo) == ""
    assert _show(repo, f"origin/{branch}", ref).status == "done"


# --- exit failures keep the launch result -------------------------------------


def _break_remote(repo):
    repo.git("remote", "set-url", "origin", str(repo.root / "missing.git"))


def test_push_failure_stops_on_branch_and_fails_launch(tb, monkeypatch, capfd):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)

    def work(env):
        _break_remote(repo)
        _bump(ref.id_slug)

    _agent(monkeypatch, work)
    with pytest.raises(LaunchBail) as exc:
        launch(ref.id_slug, agent_override="claude")
    assert exc.value.code != 0
    assert _branch(repo) == branch
    err = capfd.readouterr().err
    assert "git push origin" in err and "failed" in err


@pytest.mark.parametrize("kind", ["agent-failure", "timeout", "interrupt"])
def test_exit_failure_keeps_original_failure(tb, monkeypatch, capfd, kind):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("switch", branch)
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "4 (implement)"
    ticket.write(ref.ticket_path)
    repo.git("commit", "-qam", "to implement")
    repo.git("switch", "main")

    def work(env):
        _break_remote(repo)
        if kind == "agent-failure":
            return ReplOutcome(7, "natural")
        if kind == "timeout":
            return ReplOutcome(_TIMEOUT_EXIT_CODE, "timeout", "idle")
        raise SystemExit(130)

    _agent(monkeypatch, work)
    with pytest.raises(LaunchBail) as exc:
        launch(ref.id_slug)
    expected = {"agent-failure": 7, "timeout": _TIMEOUT_EXIT_CODE, "interrupt": 130}[kind]
    assert exc.value.code == expected
    err = capfd.readouterr().err
    assert "exit hook failed" in err and "had already failed" in err
    assert _branch(repo) == branch


def test_interrupt_during_script_step_still_runs_exit(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("switch", branch)
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "3 (open-branch)"
    ticket.write(ref.ticket_path)
    repo.git("commit", "-qam", "to open-branch")
    repo.git("switch", "main")

    def interrupted(*args, **kwargs):
        (repo.root / "partial.txt").write_text("x\n", encoding="utf-8")
        raise KeyboardInterrupt

    monkeypatch.setattr(launch_module, "run_script_chain", interrupted)
    with pytest.raises(KeyboardInterrupt):
        launch(ref.id_slug)
    assert _branch(repo) == "main"
    assert repo.git("show", f"origin/{branch}:partial.txt") == "x\n"


@pytest.mark.parametrize("exit_error", [SystemExit(130), OSError("could not spawn exit")])
def test_exit_exception_keeps_prior_launch_result(tb, monkeypatch, exit_error):
    _, ref = tb
    real = launch_module.run_launch_hook

    def fail_exit(cfg, target, script, phase, scope):
        if phase == "exit":
            raise exit_error
        return real(cfg, target, script, phase, scope)

    monkeypatch.setattr(launch_module, "run_launch_hook", fail_exit)
    _agent(monkeypatch, lambda env: ReplOutcome(_TIMEOUT_EXIT_CODE, "timeout", "idle"))
    result = launch(ref.id_slug, return_timeout=True)
    assert (result.kind, result.exit_code) == ("timeout", _TIMEOUT_EXIT_CODE)


def test_interrupt_after_enter_switch_records_new_branch_and_returns(tb, monkeypatch):
    repo, ref = tb
    real = launch_module.run_launch_hook

    def hook(cfg, target, script, phase, scope):
        if phase == "enter":
            edge_enter = runpy.run_path(str(script))["enter"]
            run_op = edge_enter.__globals__["run_op"]

            def interrupt_after_switch(operation, *args):
                run_op(operation, *args)
                raise KeyboardInterrupt

            with monkeypatch.context() as patch:
                patch.setenv("COGA_TASK_TICKET", str(target.ticket_path))
                patch.setenv("COGA_TASK_SLUG", target.id_slug)
                patch.setenv("TMPDIR", str(scope.path))
                patch.setitem(edge_enter.__globals__, "run_op", interrupt_after_switch)
                edge_enter()
        return real(cfg, target, script, phase, scope)

    monkeypatch.setattr(launch_module, "run_launch_hook", hook)
    with pytest.raises(KeyboardInterrupt):
        launch(ref.id_slug)
    assert _branch(repo) == "main"
    branch, = _remote_branches(repo) - {"main"}
    assert read_dev_fields(_show(repo, f"origin/{branch}", ref).body) == {
        "branch": branch, "base": "main", "remote": "origin",
    }
    monkeypatch.setattr(launch_module, "run_launch_hook", real)
    _agent(monkeypatch, lambda env: _bump(ref.id_slug))
    assert launch(ref.id_slug).exit_code == 0
    assert _remote_branches(repo) == {"main", branch}
    assert _show(repo, f"origin/{branch}", ref).step == "2 (review-design)"


def test_agent_deleting_ticket_still_commits_and_pushes(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)

    def delete(env):
        ref.ticket_path.unlink()

    _agent(monkeypatch, delete)
    assert launch(ref.id_slug, agent_override="claude").exit_code == 0
    assert _branch(repo) == "main"
    subject = repo.git("log", "-1", "--format=%s", f"origin/{branch}").strip()
    assert subject == f"{ref.id_slug}: launch handoff (ticket removed)"


# --- enter refusals --------------------------------------------------------------


def _enter_refusal(ref) -> str:
    with pytest.raises(LaunchBail) as exc:
        launch(ref.id_slug)
    return exc.value.reason


def test_enter_refuses_detached_head(tb, capfd):
    repo, ref = tb
    repo.git("switch", "--detach")
    _enter_refusal(ref)
    assert "detached" in capfd.readouterr().err
    assert read_ticket(ref).status == "active"


def test_enter_refuses_dirty_switch_and_names_files(tb, capfd):
    repo, ref = tb
    (repo.root / "scratch.txt").write_text("x\n", encoding="utf-8")
    _enter_refusal(ref)
    err = capfd.readouterr().err
    assert "scratch.txt" in err and "coga sync" in err
    assert _branch(repo) == "main"
    assert read_ticket(ref).status == "active"


def test_dirty_tree_allowed_without_switch(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("switch", branch)
    (repo.root / "wip.txt").write_text("wip\n", encoding="utf-8")
    _agent(monkeypatch, lambda env: _bump(ref.id_slug))
    assert launch(ref.id_slug, agent_override="claude").exit_code == 0
    assert _branch(repo) == branch
    assert repo.git("show", f"origin/{branch}:wip.txt") == "wip\n"


def test_enter_refuses_multiple_candidate_branches(tb, monkeypatch, capfd):
    repo, ref = tb
    from coga_edge.git_workflow import branch_slug_part

    part = branch_slug_part(ref.id_slug)
    for name in (f"coga/{part}-aaaaaa", f"coga/{part}-bbbbbb"):
        repo.git("switch", "-q", "-c", name, "main")
        replace_blackboard(
            ref.ticket_path,
            set_dev_fields(read_blackboard(ref.ticket_path), branch=name, base="main", remote="origin"),
        )
        repo.git("commit", "-qam", name)
    repo.git("switch", "-q", "main")
    _enter_refusal(ref)
    assert "more than one branch" in capfd.readouterr().err


@pytest.mark.parametrize("remote_removes_ticket", [False, True])
def test_enter_refuses_diverged_local_and_remote(tb, monkeypatch, capfd, remote_removes_ticket):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("switch", "-q", branch)
    (repo.root / "local.txt").write_text("l\n", encoding="utf-8")
    repo.git("add", "local.txt")
    repo.git("commit", "-qm", "local")
    repo.git("reset", "-q", "--hard", "HEAD~1")
    (repo.root / "other.txt").write_text("o\n", encoding="utf-8")
    repo.git("add", "other.txt")
    if remote_removes_ticket:
        repo.git("rm", str(ref.ticket_path))
    repo.git("commit", "-qm", "other")
    repo.git("push", "-q", "--force", "origin", branch)
    repo.git("reset", "-q", "--hard", "HEAD~1")
    (repo.root / "third.txt").write_text("t\n", encoding="utf-8")
    repo.git("add", "third.txt")
    repo.git("commit", "-qm", "third")
    repo.git("switch", "-q", "main")
    _enter_refusal(ref)
    assert "diverged" in capfd.readouterr().err
    assert _branch(repo) == "main"
    assert read_ticket(ref).status == "active"


def test_resume_creates_local_tracking_branch_from_recorded_remote(tb, monkeypatch):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("branch", "-D", branch)
    seen = _agent(monkeypatch, lambda env: _bump(ref.id_slug))
    assert launch(ref.id_slug, agent_override="claude").exit_code == 0
    assert seen[0]["COGA_TASK_STEP"] == "2 (review-design)"
    assert _branch(repo) == "main"
    assert repo.git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}").strip() == f"origin/{branch}"


@pytest.mark.parametrize("fields,needle", [
    ({"branch": "coga/gone", "base": "main", "remote": "origin"}, "exists neither"),
    ({"branch": "coga/gone"}, "without base: or remote:"),
])
def test_enter_refuses_bad_recorded_branch(tb, capfd, fields, needle):
    repo, ref = tb
    replace_blackboard(ref.ticket_path, set_dev_fields(read_blackboard(ref.ticket_path), **fields))
    repo.git("commit", "-qam", "record")
    _enter_refusal(ref)
    assert needle in capfd.readouterr().err
    assert read_ticket(ref).status == "active"


def test_ticket_only_on_branch_warns(tb, monkeypatch, capfd):
    repo, ref = tb
    branch = _first_launch(repo, ref, monkeypatch)
    repo.git("rm", "-q", str(ref.ticket_path))
    repo.git("commit", "-qm", "drop ticket on main")
    repo.git("switch", "-q", branch)
    capfd.readouterr()
    _agent(monkeypatch, lambda env: _bump(ref.id_slug))
    assert launch(ref.id_slug, agent_override="claude").exit_code == 0
    err = capfd.readouterr().err
    assert err.count("ticket exists only on its branch; commit it on `main`") == 2


# --- the edge script directly --------------------------------------------------


def _run_hook(repo, ref, phase, tmp: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COGA_")}
    env.update(TMPDIR=str(tmp), COGA_TASK_TICKET=str(ref.ticket_path), COGA_TASK_SLUG=ref.id_slug)
    return subprocess.run(
        [sys.executable, str(_HOOK), phase], cwd=repo.root, env=env, text=True, capture_output=True,
    )


def test_exit_with_clean_tree_pushes_unpushed_commits(tb, tmp_path):
    repo, ref = tb
    repo.git("switch", "-q", "-c", "coga/x")
    (repo.root / "a.txt").write_text("a\n", encoding="utf-8")
    repo.git("add", "a.txt")
    repo.git("commit", "-qm", "unpushed")
    state = tmp_path / "state"
    state.mkdir()
    (state / "git-ticket-branch.json").write_text(json.dumps(
        {"start": "main", "branch": "coga/x", "remote": "origin", "slug": ref.id_slug}
    ))
    before = repo.git("rev-parse", "HEAD").strip()
    result = _run_hook(repo, ref, "exit", state)
    assert result.returncode == 0, result.stderr
    assert repo.git("--git-dir", str(repo.origin), "rev-parse", "coga/x").strip() == before
    assert _branch(repo) == "main"


def test_exit_refuses_when_head_left_ticket_branch(tb, tmp_path):
    repo, ref = tb
    (tmp_path / "git-ticket-branch.json").write_text(json.dumps(
        {"start": "main", "branch": "coga/x", "remote": "origin", "slug": ref.id_slug}
    ))
    result = _run_hook(repo, ref, "exit", tmp_path)
    assert result.returncode != 0
    assert "not the ticket branch" in result.stderr


def test_exit_without_enter_state_is_a_no_op(tb, tmp_path):
    repo, ref = tb
    result = _run_hook(repo, ref, "exit", tmp_path)
    assert result.returncode == 0 and result.stderr == ""


# --- other runners refuse ticket-branch --------------------------------------


def test_megalaunch_skips_ticket_branch_ticket(tb):
    from coga_edge.megalaunch import _candidate_result

    repo, ref = tb
    cfg = load_config(repo.coga_os)
    result = _candidate_result(cfg, ref, read_ticket(ref))
    assert result is not None and result.outcome == "skipped-unlaunchable"
    assert "git: ticket-branch" in result.detail


def test_recurring_template_with_ticket_branch_is_refused_before_period_changes(tb, capsys):
    from coga.paths import log_path
    from coga.recurring import create_named, scan_due
    from coga.recurring_runner import run_recurring_named
    from coga.validate import run as validate_run

    repo, _ = tb
    cfg = load_config(repo.coga_os)
    template = repo.coga_os / "recurring" / "nightly" / "ticket.md"
    template.parent.mkdir(parents=True)
    source = '---\ntitle: Nightly\nschedule: "0 0 * * *"\nworkflow: plain\n---\n\nRun nightly.\n'
    template.write_text(source, encoding="utf-8")
    period = create_named(cfg, "nightly").ref.ticket_path
    before = period.read_bytes(), log_path(cfg).read_bytes()
    template.write_text(source.replace("workflow: plain", "workflow: tb"), encoding="utf-8")

    assert any(
        issue.kind == "bad-shape" and "`git: ticket-branch`" in issue.message
        for issue in validate_run(cfg).issues
    )
    assert any(
        name == "nightly" and "`git: ticket-branch`" in reason
        for name, reason in scan_due(cfg, force=True).errors
    )
    assert run_recurring_named(cfg, "nightly") == 2
    assert "`git: ticket-branch`" in capsys.readouterr().err
    assert before == (period.read_bytes(), log_path(cfg).read_bytes())
