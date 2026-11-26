"""Workflow-declared `enter` / `exit` step scripts: parsing, freezing, call points."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

import coga.launch as launch_module
from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.launch import launch
from coga.repl_supervisor import ReplOutcome
from coga.tasks import read_ticket, resolve_task
from coga.workflow import Workflow, WorkflowError, step_script

WORKFLOW = """---
name: ss
description: Step-script test workflow.
enter: test/enter
exit: test/exit
steps:
  - name: prepare
    assignee: agent
    run: test/advance
  - name: implement
    assignee: agent
  - name: review
    assignee: owner
---

## implement
Implement it.

## review
Review it.
"""

_RECORDER = """\
import os, re, sys
from pathlib import Path
text = Path(os.environ["COGA_TASK_TICKET"]).read_text()
step = re.search(r"^step: (.*)$", text, re.M)
Path(os.environ["STEP_SCRIPT_LOG"]).open("a").write(
    "{kind} " + (step.group(1).strip("'\\"") if step else "-") + " "
    + ("supervised" if os.environ.get("COGA_SUPERVISED") else "plain") + "\\n"
)
sys.exit(int(os.environ.get("{kind}_EXIT_CODE", "0")))
"""

_ADVANCE = """\
import os, subprocess, sys
subprocess.run([sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]], check=True)
"""


@pytest.fixture
def ss(git_repo, monkeypatch, tmp_path):
    repo = git_repo
    with (repo.coga_os / "coga.local.toml").open("a", encoding="utf-8") as stream:
        stream.write("\n[notification.slack]\nenabled = false\n")
    (repo.coga_os / "workflows" / "ss.md").write_text(WORKFLOW, encoding="utf-8")
    for kind in ("enter", "exit"):
        skill = repo.coga_os / "skills" / "test" / kind
        skill.mkdir(parents=True)
        (skill / "run.py").write_text(_RECORDER.replace("{kind}", kind), encoding="utf-8")
    advance = repo.coga_os / "skills" / "test" / "advance"
    advance.mkdir(parents=True)
    (advance / "run.py").write_text(_ADVANCE, encoding="utf-8")
    cfg = load_config(repo.coga_os)
    created = create_task(
        cfg=cfg, title="Step scripts", workflow_name="ss", contexts=[],
        owner=cfg.current_user, agent=cfg.default_agent().name, status="active",
    )
    ref = resolve_task(cfg, created["slug"])
    for key in [k for k in os.environ if k.startswith("COGA_") and k != "COGA_SYSTEM_TMPDIR"]:
        monkeypatch.delenv(key)
    log = tmp_path / "step-scripts.log"
    monkeypatch.setenv("STEP_SCRIPT_LOG", str(log))
    monkeypatch.setattr(launch_module, "interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(launch_module.shutil, "which", lambda name, **kwargs: f"/usr/bin/{name}")
    monkeypatch.setattr(launch_module.usage_tracking, "capture_session", lambda **kwargs: None)
    return repo, ref, log


def _calls(log: Path) -> list[str]:
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


# --- workflow fields -----------------------------------------------------------


def test_enter_exit_parse_and_freeze_after_name(tmp_path):
    path = tmp_path / "w.md"
    path.write_text(WORKFLOW, encoding="utf-8")
    wf = Workflow.load(path)
    assert (wf.enter, wf.exit) == ("test/enter", "test/exit")
    frozen = wf.freeze()
    assert list(frozen) == ["name", "enter", "exit", "steps"]

    path.write_text(WORKFLOW.replace("enter: test/enter\n", ""), encoding="utf-8")
    frozen = Workflow.load(path).freeze()
    assert list(frozen) == ["name", "exit", "steps"]


@pytest.mark.parametrize("bad", ["enter: ''", "enter: [a]", "enter: 3"])
def test_malformed_step_script_ref_is_refused(tmp_path, bad):
    path = tmp_path / "w.md"
    path.write_text(WORKFLOW.replace("enter: test/enter", bad), encoding="utf-8")
    with pytest.raises(WorkflowError, match="`enter`"):
        Workflow.load(path)


@pytest.mark.parametrize("mode", ["ticket-branch", "trunk"])
def test_removed_git_field_is_refused_with_the_migration(tmp_path, mode):
    path = tmp_path / "w.md"
    path.write_text(WORKFLOW.replace("enter:", f"git: {mode}\nenter:"), encoding="utf-8")
    with pytest.raises(WorkflowError, match="names the migration"):
        Workflow.load(path)


def test_git_main_is_still_accepted_and_not_frozen(tmp_path):
    path = tmp_path / "w.md"
    path.write_text(WORKFLOW.replace("enter:", "git: main\nenter:"), encoding="utf-8")
    assert "git" not in Workflow.load(path).freeze()


def _leftover_git_mode(ref) -> None:  # type: ignore[no-untyped-def]
    ticket = read_ticket(ref)
    ticket.frontmatter["workflow"] = {"name": "ss", "git": "ticket-branch",
                                      "steps": ticket.workflow["steps"]}
    ticket.write(ref.ticket_path)


def test_leftover_frozen_git_mode_is_reported_and_refused(ss):
    from coga.validate import run as validate_run
    from coga_edge.megalaunch import _candidate_result

    repo, ref, log = ss
    _leftover_git_mode(ref)
    cfg = load_config(repo.coga_os)
    assert any(
        issue.kind == "bad-shape" and "workflow.git 'ticket-branch'" in issue.message
        and "names the migration" in issue.message
        for issue in validate_run(cfg).issues
    )
    with pytest.raises(launch_module.LaunchBail, match="names the migration"):
        launch(ref.id_slug)
    result = _candidate_result(cfg, ref, read_ticket(ref))
    assert result is not None and result.outcome == "skipped-unlaunchable"
    assert "names the migration" in result.detail
    assert _calls(log) == []


def test_step_script_reads_frozen_and_draft(ss):
    repo, _, _ = ss
    cfg = load_config(repo.coga_os)
    assert step_script(None, cfg, "exit") is None
    assert step_script({"name": "x", "steps": []}, cfg, "exit") is None
    assert step_script({"name": "x", "exit": "a/b", "steps": []}, cfg, "exit") == "a/b"
    assert step_script("ss", cfg, "enter") == "test/enter"
    with pytest.raises(WorkflowError):
        step_script({"name": "x", "exit": 5, "steps": []}, cfg, "exit")


def test_validate_reports_unresolvable_frozen_step_script(ss):
    from coga.validate import run as validate_run

    repo, ref, _ = ss
    ticket = read_ticket(ref)
    ticket.frontmatter["workflow"]["exit"] = "test/missing"
    ticket.write(ref.ticket_path)
    issues = [
        issue for issue in validate_run(load_config(repo.coga_os)).issues
        if issue.kind == "bad-shape" and "workflow.exit" in issue.message
    ]
    assert issues and issues[0].severity == "error"


# --- exit on step changes --------------------------------------------------------


def _set_in_progress(ref, step: str | None = None) -> None:
    ticket = read_ticket(ref)
    ticket.frontmatter["status"] = "in_progress"
    if step is not None:
        ticket.frontmatter["step"] = step
    ticket.write(ref.ticket_path)


def test_bump_runs_exit_once_after_the_write(ss):
    _, ref, log = ss
    _set_in_progress(ref, "2 (implement)")
    result = CliRunner().invoke(app, ["bump", ref.id_slug])
    assert result.exit_code == 0, result.output
    # The script saw the new step: it runs after the local write.
    assert _calls(log) == ["exit 3 (review) plain"]


def test_final_bump_runs_exit_once(ss):
    _, ref, log = ss
    _set_in_progress(ref, "3 (review)")
    result = CliRunner().invoke(app, ["bump", ref.id_slug])
    assert result.exit_code == 0, result.output
    assert read_ticket(ref).status == "done"
    assert _calls(log) == ["exit - plain"]


@pytest.mark.parametrize("argv", [
    ["mark", "done", "{slug}"],
    ["mark", "canceled", "{slug}", "--message", "no longer needed"],
    ["block", "--task", "{slug}", "--reason", "Need an answer"],
])
def test_mark_and_block_run_exit(ss, argv):
    _, ref, log = ss
    _set_in_progress(ref)
    result = CliRunner().invoke(app, [a.replace("{slug}", ref.id_slug) for a in argv])
    assert result.exit_code == 0, result.output
    assert len(_calls(log)) == 1 and _calls(log)[0].startswith("exit ")


def test_mark_active_and_paused_do_not_run_exit(ss):
    _, ref, log = ss
    assert CliRunner().invoke(app, ["mark", "paused", ref.id_slug]).exit_code == 0
    assert CliRunner().invoke(app, ["mark", "active", ref.id_slug]).exit_code == 0
    assert _calls(log) == []


def test_failed_exit_keeps_the_write_and_fails_the_command(ss, monkeypatch):
    _, ref, log = ss
    _set_in_progress(ref, "2 (implement)")
    monkeypatch.setenv("exit_EXIT_CODE", "7")
    result = CliRunner().invoke(app, ["bump", ref.id_slug])
    assert result.exit_code == 7
    assert "exit script 'test/exit' failed (exit 7)" in result.output
    assert read_ticket(ref).step == "3 (review)"


# --- enter at step start -------------------------------------------------------


def test_launch_runs_enter_before_each_step_and_exit_on_each_bump(ss, monkeypatch):
    _, ref, log = ss
    seen_steps: list[str] = []

    def fake(cmd, env, **kwargs):  # type: ignore[no-untyped-def]
        seen_steps.append(read_ticket(ref).step)
        result = CliRunner().invoke(app, ["bump", ref.id_slug], env=dict(env))
        assert result.exit_code == 0, result.output
        return ReplOutcome(0, "natural")

    monkeypatch.setattr(launch_module, "run_with_done_marker", fake)
    assert launch(ref.id_slug).exit_code == 0
    assert seen_steps == ["2 (implement)"]
    assert _calls(log) == [
        "enter 1 (prepare) plain",   # before the script step
        "exit 2 (implement) plain",  # the script's bump
        "enter 2 (implement) plain",  # before the agent step
        "exit 3 (review) plain",     # the agent's supervised bump
    ]
    # The owner step is not started by launch, so no further enter.
    assert read_ticket(ref).step == "3 (review)"


def test_failed_enter_refuses_the_step(ss, monkeypatch):
    _, ref, log = ss
    monkeypatch.setenv("enter_EXIT_CODE", "5")
    from coga.launch import LaunchBail

    with pytest.raises(LaunchBail) as exc:
        launch(ref.id_slug)
    assert exc.value.code == 5
    assert _calls(log) == ["enter 1 (prepare) plain"]
    assert read_ticket(ref).step == "1 (prepare)"


def test_recurring_template_with_step_scripts_is_refused(ss):
    from coga.recurring import RecurringError, Template, assert_template_step_scripts

    repo, _, _ = ss
    cfg = load_config(repo.coga_os)
    template = Template.__new__(Template)
    object.__setattr__(template, "name", "nightly")
    object.__setattr__(template, "frontmatter", {"workflow": "ss"})
    with pytest.raises(RecurringError, match="step scripts"):
        assert_template_step_scripts(cfg, template)
