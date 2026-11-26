"""`git/ticket-enter` and `git/ticket-exit` against a real repo and a bare remote."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import coga.launch as launch_module
from coga.blackboard import read_dev_fields
from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.launch import AgentSessionResult, launch
from coga.repl_supervisor import ReplOutcome
from coga.taskfile import read_blackboard
from coga.tasks import read_ticket, resolve_task
from coga.ticket import Ticket

_SKILLS = Path(__file__).resolve().parents[1] / "src/coga/resources/templates/coga/bootstrap/skills"

WORKFLOW = """---
name: te
description: Enter/exit test workflow.
enter: git/ticket-enter
exit: git/ticket-exit
steps:
  - name: implement
    assignee: agent
  - name: polish
    assignee: agent
  - name: review
    assignee: owner
---

## implement
Implement it.

## polish
Polish it.

## review
Review it.
"""


@pytest.fixture
def te(git_repo, monkeypatch):
    repo = git_repo
    with (repo.root / ".gitignore").open("a", encoding="utf-8") as stream:
        stream.write("coga/.coga/\n")
    with (repo.coga_os / "coga.local.toml").open("a", encoding="utf-8") as stream:
        stream.write("\n[notification.slack]\nenabled = false\n")
    (repo.coga_os / "workflows" / "te.md").write_text(WORKFLOW, encoding="utf-8")
    cfg = load_config(repo.coga_os)
    created = create_task(
        cfg=cfg, title="Branch work", workflow_name="te", contexts=[],
        owner=cfg.current_user, agent=cfg.default_agent().name, status="active",
    )
    other = create_task(
        cfg=cfg, title="Other work", workflow_name="te", contexts=[],
        owner=cfg.current_user, agent=cfg.default_agent().name, status="active",
    )
    ref = resolve_task(cfg, created["slug"])
    other_ref = resolve_task(cfg, other["slug"])
    repo.git("add", "-A")
    repo.git("commit", "-m", "Seed tickets")
    repo.git("push", "origin", "main")
    for key in [k for k in os.environ if k.startswith("COGA_") and k != "COGA_SYSTEM_TMPDIR"]:
        monkeypatch.delenv(key)
    monkeypatch.setattr(launch_module, "interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(launch_module.shutil, "which", lambda name, **kwargs: f"/usr/bin/{name}")
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", lambda **kwargs: None)
    return repo, ref, other_ref


def _agent(monkeypatch, action):
    def fake(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        outcome = action(env)
        return outcome if isinstance(outcome, ReplOutcome) else ReplOutcome(0, "natural")

    monkeypatch.setattr(launch_module, "run_with_done_marker", fake)


def _invoke(*argv: str, env: dict | None = None):
    return CliRunner().invoke(app, list(argv), env=env)


def _branch(repo) -> str:
    return repo.git("branch", "--show-current").strip()


def _rel(repo, path: Path) -> str:
    return path.resolve().relative_to(repo.root.resolve()).as_posix()


def _show(repo, rev: str, path: Path) -> str:
    return repo.git("show", f"{rev}:{_rel(repo, path)}")


def _remote_ticket(repo, ref) -> Ticket:
    repo.git("fetch", "-q", "origin")
    return Ticket.parse(_show(repo, "origin/main", ref.ticket_path))


def _bump_from(env: dict, slug: str) -> None:
    result = _invoke("bump", slug, env=dict(env))
    assert result.exit_code == 0, result.output


def _implement_step(repo, ref, monkeypatch, *, extra=None) -> dict:
    """Run `implement` from main: write code, bump; return observations."""
    observed: dict = {}

    def action(env):  # type: ignore[no-untyped-def]
        observed["branch"] = _branch(repo)
        observed["dev"] = read_dev_fields(read_blackboard(ref.ticket_path))
        (repo.root / "feature.txt").write_text("feature\n", encoding="utf-8")
        if extra:
            extra()
        _bump_from(env, ref.id_slug)
        return ReplOutcome(0, "natural")

    _agent(monkeypatch, action)
    return observed


def test_first_step_branches_commits_code_and_publishes_only_the_ticket(te, monkeypatch):
    repo, ref, other_ref = te
    # Another ticket's uncommitted edit and an unpushed local main commit
    # must never be published.
    other_before = other_ref.ticket_path.read_text(encoding="utf-8")
    other_ref.ticket_path.write_text(other_before + "\nlocal note\n", encoding="utf-8")
    (repo.root / "local-only.txt").write_text("x\n", encoding="utf-8")
    repo.git("add", "local-only.txt")
    repo.git("commit", "-qm", "local only")
    local_main = repo.git("rev-parse", "main").strip()

    observed: dict = {}

    def action(env):  # type: ignore[no-untyped-def]
        observed.setdefault("branches", []).append(_branch(repo))
        step = read_ticket(ref).step
        if step == "1 (implement)":
            observed["dev"] = read_dev_fields(read_blackboard(ref.ticket_path))
            (repo.root / "feature.txt").write_text("feature\n", encoding="utf-8")
        _bump_from(env, ref.id_slug)
        return ReplOutcome(0, "natural")

    _agent(monkeypatch, action)
    assert launch(ref.id_slug).exit_code == 0

    branch = observed["dev"]["branch"]
    assert observed["dev"] == {"branch": branch, "base": "main", "remote": "origin"}
    # Each agent step ran on the branch; the checkout ends on the base.
    assert observed["branches"] == [branch, branch]
    assert _branch(repo) == "main"

    # The base on the remote has the live ticket (owner review step, Dev record).
    published = _remote_ticket(repo, ref)
    assert published.step == "3 (review)"
    assert read_dev_fields(read_blackboard(ref.ticket_path))["branch"] == branch
    assert f"[{ref.id_slug}]" in _show(repo, "origin/main", repo.coga_os / "log.md")
    # Only the ticket and the log changed on the published base.
    changed = repo.git("diff", "--name-only", "origin/main~1", "origin/main").split()
    assert set(changed) <= {_rel(repo, ref.ticket_path), _rel(repo, repo.coga_os / "log.md")}
    assert _show(repo, "origin/main", other_ref.ticket_path) == other_before
    assert "local-only.txt" not in repo.git("ls-tree", "-r", "--name-only", "origin/main")
    # Local main kept its unpushed commit (not an ancestor, so no fast-forward).
    assert repo.git("rev-parse", "main").strip() == local_main
    assert other_ref.ticket_path.read_text(encoding="utf-8").endswith("local note\n")

    # The code branch carries the code and no ticket state.
    assert _show(repo, f"origin/{branch}", repo.root / "feature.txt") == "feature\n"
    branch_paths = repo.git("diff", "--name-only", "main", f"origin/{branch}").split()
    assert not any(p.startswith("coga/tasks/") or p == "coga/log.md" for p in branch_paths
                   if p != "local-only.txt")


def test_fast_forwards_local_base_when_it_has_no_local_commits(te, monkeypatch):
    repo, ref, _ = te
    _implement_step(repo, ref, monkeypatch)
    assert launch(ref.id_slug).exit_code == 0
    assert _branch(repo) == "main"
    assert repo.git("rev-parse", "main").strip() == repo.git("rev-parse", "origin/main").strip()
    assert _show(repo, "main", ref.ticket_path) == ref.ticket_path.read_text(encoding="utf-8")


def test_exit_preserves_another_tickets_staged_and_unstaged_changes(te, monkeypatch):
    repo, ref, other = te
    other_rel = _rel(repo, other.ticket_path)
    original = other.ticket_path.read_text(encoding="utf-8")
    staged = original + "\nstaged note\n"
    working = staged + "\nunstaged note\n"

    def action(env):
        if read_ticket(ref).step == "1 (implement)":
            other.ticket_path.write_text(staged, encoding="utf-8")
            repo.git("add", "--", other_rel)
            other.ticket_path.write_text(working, encoding="utf-8")
            (repo.root / "feature.txt").write_text("feature\n", encoding="utf-8")
        _bump_from(env, ref.id_slug)

    _agent(monkeypatch, action)
    assert launch(ref.id_slug).exit_code == 0
    branch = read_dev_fields(read_blackboard(ref.ticket_path))["branch"]
    assert repo.git("diff", "--name-only", f"origin/main...origin/{branch}").splitlines() == [
        "feature.txt",
    ]
    assert repo.git("show", f":{other_rel}") == staged
    assert other.ticket_path.read_text(encoding="utf-8") == working
    assert _show(repo, "origin/main", other.ticket_path) == original


def test_exit_refuses_a_staged_carried_ticket_without_overwriting_it(te, monkeypatch, capfd):
    repo, ref, _ = te
    observed = {}

    def action(env):
        rel = _rel(repo, ref.ticket_path)
        repo.git("add", "--", rel)
        observed["staged"] = repo.git("show", f":{rel}")
        (repo.root / "feature.txt").write_text("feature\n", encoding="utf-8")
        result = _invoke("bump", ref.id_slug, env=dict(env))
        assert result.exit_code == 1

    _agent(monkeypatch, action)
    with pytest.raises(launch_module.LaunchBail, match="Stopping before the next step"):
        launch(ref.id_slug)
    assert "Unstage the carried ticket or log" in capfd.readouterr().err
    assert _branch(repo) == read_dev_fields(read_blackboard(ref.ticket_path))["branch"]
    assert repo.git("show", f":{_rel(repo, ref.ticket_path)}") == observed["staged"]
    assert read_ticket(ref).step == "2 (polish)"
    assert "feature.txt" not in repo.git("ls-tree", "--name-only", "HEAD")


def test_directory_ticket_publishes_git_visible_attachments_and_deletions(te):
    repo, _, _ = te
    cfg = load_config(repo.coga_os)
    created = create_task(
        cfg=cfg, title="Directory ticket", workflow_name="te", contexts=[],
        owner=cfg.current_user, agent=cfg.default_agent().name, status="active",
        force_directory=True,
    )
    ref = resolve_task(cfg, created["slug"])
    directory = ref.ticket_path.parent
    rel = _rel(repo, directory)
    notes = directory / "old.md"
    notes.write_text("old\n", encoding="utf-8")
    (directory / ".gitignore").write_text("private.txt\n", encoding="utf-8")
    repo.git("add", "--", rel)
    repo.git("commit", "-qm", "Seed directory ticket")
    repo.git("push", "-q", "origin", "main")

    notes.unlink()
    (directory / "public notes.txt").write_text("public\n", encoding="utf-8")
    ignored = directory / "private.txt"
    ignored.write_text("local-only\n", encoding="utf-8")
    nested = directory / "nested"
    nested.mkdir()
    (nested / "ticket.md").write_text("nested\n", encoding="utf-8")
    (nested / "notes.txt").write_text("nested work\n", encoding="utf-8")

    result = _invoke("mark", "done", ref.id_slug)
    assert result.exit_code == 0, result.output
    assert _remote_ticket(repo, ref).status == "done"
    assert repo.git("ls-tree", "-r", "--name-only", "origin/main", "--", rel).splitlines() == [
        f"{rel}/.gitignore", f"{rel}/public notes.txt", f"{rel}/ticket.md",
    ]
    assert ignored.read_text(encoding="utf-8") == "local-only\n"
    assert (nested / "notes.txt").read_text(encoding="utf-8") == "nested work\n"


def test_resume_switches_to_recorded_branch_with_the_live_ticket(te, monkeypatch):
    repo, ref, _ = te
    seen: list[tuple[str, str]] = []

    def action(env):  # type: ignore[no-untyped-def]
        seen.append((_branch(repo), read_ticket(ref).step))
        if read_ticket(ref).step == "1 (implement)":
            (repo.root / "feature.txt").write_text("feature\n", encoding="utf-8")
            _bump_from(env, ref.id_slug)
            return ReplOutcome(0, "natural")
        return ReplOutcome(0, "natural")  # polish: session ends without a bump

    _agent(monkeypatch, action)
    assert launch(ref.id_slug).exit_code == 0
    branch = read_dev_fields(read_blackboard(ref.ticket_path))["branch"]
    # The polish session ended without a step change: no exit ran.
    assert _branch(repo) == branch
    assert seen == [(branch, "1 (implement)"), (branch, "2 (polish)")]

    # Back on main by hand (as `coga sync` would), then resume: enter switches
    # to the recorded branch carrying the live ticket.
    live = ref.ticket_path.read_bytes()
    repo.git("checkout", "HEAD", "--", _rel(repo, ref.ticket_path), _rel(repo, repo.coga_os / "log.md"))
    repo.git("switch", "main")
    ref.ticket_path.write_bytes(live)
    seen.clear()

    def polish(env):  # type: ignore[no-untyped-def]
        seen.append((_branch(repo), read_ticket(ref).step))
        _bump_from(env, ref.id_slug)

    _agent(monkeypatch, polish)
    assert launch(ref.id_slug).exit_code == 0
    assert seen == [(branch, "2 (polish)")]
    assert _branch(repo) == "main"
    assert _remote_ticket(repo, ref).step == "3 (review)"


def test_owner_bump_outside_launch_publishes(te, monkeypatch):
    repo, ref, _ = te
    _implement_step(repo, ref, monkeypatch)
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "3 (review)"
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    result = _invoke("bump", ref.id_slug)
    assert result.exit_code == 0, result.output
    assert _remote_ticket(repo, ref).status == "done"
    assert _branch(repo) == "main"


def test_block_publishes_and_returns_to_base(te, monkeypatch):
    repo, ref, _ = te

    def action(env):  # type: ignore[no-untyped-def]
        (repo.root / "wip.txt").write_text("wip\n", encoding="utf-8")
        result = _invoke("block", "--task", ref.id_slug, "--reason", "Need a decision", env=dict(env))
        assert result.exit_code == 0, result.output

    _agent(monkeypatch, action)
    assert launch(ref.id_slug).exit_code == 0
    assert _branch(repo) == "main"
    assert _remote_ticket(repo, ref).status == "blocked"
    branch = read_dev_fields(read_blackboard(ref.ticket_path))["branch"]
    assert _show(repo, f"origin/{branch}", repo.root / "wip.txt") == "wip\n"


def test_rejected_publish_fails_loudly_without_retry(te, monkeypatch):
    repo, ref, _ = te
    hook = repo.origin / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nwhile read old new name; do\n"
                    "  [ \"$name\" = refs/heads/main ] && { echo rejected >&2; exit 1; }\n"
                    "done\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    codes: list[int] = []

    def action(env):  # type: ignore[no-untyped-def]
        result = _invoke("bump", ref.id_slug, env=dict(env))
        codes.append(result.exit_code)

    _agent(monkeypatch, action)
    with pytest.raises(launch_module.LaunchBail, match="Stopping before the next step"):
        launch(ref.id_slug)
    # The bump failed loudly and the supervisor did not start the next step.
    assert codes == [1]
    # The step change was written locally; the base on the remote is unchanged.
    assert read_ticket(ref).step == "2 (polish)"
    assert _remote_ticket(repo, ref).step != "2 (polish)"
    from coga.step_scripts import exit_failure

    cfg = load_config(repo.coga_os)
    assert "exit script 'git/ticket-exit' failed" in exit_failure(cfg, ref)

    # Once the remote accepts again, the next exit republishes and clears it.
    hook.unlink()
    result = _invoke("block", "--task", ref.id_slug, "--reason", "Retry later")
    assert result.exit_code == 0, result.output
    assert exit_failure(cfg, ref) is None
    assert _remote_ticket(repo, ref).status == "blocked"


def test_megalaunch_stops_when_an_entered_step_leaves_the_branch_checked_out(te, monkeypatch):
    from coga_edge.megalaunch import run_megalaunch

    repo, ref, other = te
    monkeypatch.setattr("coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True)
    started = []

    def fake_spawn(cfg, task, ticket, agent, **kwargs):
        started.append(task.id_slug)
        (repo.root / "uncommitted-feature.txt").write_text("wip\n", encoding="utf-8")
        return AgentSessionResult(0, "natural")

    monkeypatch.setattr("coga_edge.megalaunch.spawn_agent_session", fake_spawn)
    run = run_megalaunch(load_config(repo.coga_os), selection=[ref.id_slug, other.id_slug])

    assert started == [ref.id_slug]
    (result,) = run.results
    assert result.outcome == "failed"
    assert result.stops_run
    assert _branch(repo) == read_dev_fields(read_blackboard(ref.ticket_path))["branch"]
    assert (repo.root / "uncommitted-feature.txt").is_file()
    assert read_ticket(other).status == "active"


def test_rebase_keeps_the_live_ticket(te, monkeypatch):
    repo, ref, _ = te
    _implement_step(repo, ref, monkeypatch)
    assert launch(ref.id_slug).exit_code == 0
    branch = read_dev_fields(read_blackboard(ref.ticket_path))["branch"]
    # Someone lands a change on main.
    other = repo.root / "upstream.txt"
    repo.git("pull", "-q", "--ff-only", "origin", "main")
    other.write_text("upstream\n", encoding="utf-8")
    repo.git("add", "upstream.txt")
    repo.git("commit", "-qm", "upstream")
    repo.git("push", "-q", "origin", "main")

    # Go to the branch as enter would, then rebase through the script.
    live = ref.ticket_path.read_bytes() + b"\nedited on branch\n"
    for rel in (_rel(repo, ref.ticket_path), _rel(repo, repo.coga_os / "log.md")):
        repo.git("checkout", "HEAD", "--", rel)
    repo.git("switch", branch)
    ref.ticket_path.write_bytes(live)

    cfg = load_config(repo.coga_os)
    from coga.task_env import apply_task_env

    env = apply_task_env(os.environ.copy(), cfg, ref)
    env["TMPDIR"] = str(repo.root.parent / "rebase-tmp")
    Path(env["TMPDIR"]).mkdir()
    completed = subprocess.run(
        [sys.executable, str(_SKILLS / "git/ticket-enter/run.py"), "rebase"],
        cwd=repo.root, env=env, capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert (repo.root / "upstream.txt").is_file()
    assert ref.ticket_path.read_bytes() == live
    assert _branch(repo) == branch


def test_shipped_branch_workflows_declare_enter_and_exit():
    from coga.workflow import Workflow

    root = _SKILLS.parent / "workflows"
    for name in ("code/with-review", "code/with-self-review", "code/design-then-implement",
                 "code/agent-merge", "docs/with-review"):
        wf = Workflow.load(root / f"{name}.md")
        assert (wf.enter, wf.exit) == ("git/ticket-enter", "git/ticket-exit"), name
        assert "open-branch" not in [step.name for step in wf.steps], name
