"""Restart / respawn regression coverage for the `coga launch` supervisor.

The launch supervisor is supposed to *chain* across consecutive agent-owned
workflow steps: after the agent exits (having run `coga bump`), it re-reads the
ticket and spawns a **fresh** agent process for the next step — that respawn is
what users call "restart". `tests/test_repl_supervisor.py` covers the PTY-level
teardown (sentinel file -> SIGTERM -> SIGKILL) thoroughly, but nothing exercised
the higher layer: launch -> agent bumps -> supervisor respawns next step ->
agent finishes. And nothing exercised that chain with *real* git sync in the
loop, where the finished state must land on the control branch (and survive a
control branch that moved mid-session).

Both symptoms the team is chasing live near here: "restart is not working" (the
respawn) and "losing work" (state not reaching the control branch). These tests
lock in the *happy path* for both: with real git sync the chain respawns and
the finished `done` state lands on the control branch. They are the regression
guard so a change (e.g. the in-flight open-pr-gate migration) can't silently
break respawn or sync-back.

Note the `git_chain_repo` fixture must opt into real git via `real_git`; under the
autouse `_stub_git` no-op the sync-back is stubbed and the test "loses work" as
an artifact, not a finding.
"""

from __future__ import annotations

import os
import stat
import sys
from collections import deque
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

import coga
from conftest import init_git_repo
from coga.cli import app
from coga.commands.launch import AgentSessionResult
from coga.config import load_config
from coga.create import create_task
from coga.repl_supervisor import EXPECTED_STEP_ENV
from coga.tasks import list_tasks
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _chain_workflow(step_names: list[str]) -> str:
    steps = "\n".join(
        f"  - name: {name}\n    assignee: agent" for name in step_names
    )
    return dedent(
        """\
        ---
        name: chain
        description: Agent steps, for restart/respawn testing.
        steps:
        {steps}
        ---
        """
    ).format(steps=steps)


def _create_agent_task(coga_os: Path, step_names: list[str]) -> str:
    """Create an active agent task with `len(step_names)` agent steps.

    The supervisor must auto-restart (respawn a fresh agent) after each of the
    first `n-1` steps is bumped, and stop after the last.
    """
    _write(coga_os / "workflows" / "chain.md", _chain_workflow(step_names))
    cfg = load_config(coga_os)
    create_task(
        cfg=cfg,
        title="Chain restart",
        workflow_name="chain",
        contexts=[],
        mode="agent",
        owner="marc",
        human="marc",
        agent="claude",
        assignee="claude",
        watchers=[],
        status="active",
    )
    return list_tasks(cfg)[0].id_slug


class _FakeAgent:
    """Stand-in for a spawned agent REPL that drives the workflow via the CLI.

    Each `spawn_agent_session` the supervisor makes is one agent session. The
    fake records the step it ran on, then does what a real agent does as its
    last action — `coga bump` for every step but the last, `coga mark done` on
    the last — from the launch checkout. Running the *real* CLI keeps
    ticket-state advance and git sync in the loop.
    """

    def __init__(self, primary_coga_os: Path, actions: list[str], hook=None) -> None:
        self.primary_coga_os = primary_coga_os
        self.actions = deque(actions)
        self.steps: list[str] = []
        self.cwds: list[str] = []
        self.hook = hook

    def __call__(self, cfg, ref, ticket, agent, mode, *args, **kwargs):  # noqa: ANN001
        cwd = kwargs.get("cwd")
        self.steps.append(ticket.step or "")
        self.cwds.append(str(cwd) if cwd is not None else "")
        # An optional per-session hook fires before this session acts — used to
        # simulate another instance advancing the control branch mid-session.
        if self.hook is not None:
            self.hook(len(self.steps))

        # A real agent runs `coga` from its checkout's `coga/` dir; `cwd` is
        # None and the process cwd already is the primary coga OS dir.
        run_from = Path(cwd) / "coga" if cwd is not None else self.primary_coga_os
        action = self.actions.popleft() if self.actions else "mark_done"
        argv = (
            ["bump", ref.id_slug]
            if action == "bump"
            else ["mark", "done", ref.id_slug]
        )

        prev = os.getcwd()
        os.chdir(run_from)
        try:
            result = CliRunner().invoke(app, argv)
        finally:
            os.chdir(prev)
        assert result.exit_code == 0, (
            f"fake agent `coga {' '.join(argv)}` failed from {run_from}:\n"
            f"{result.output}"
        )
        return AgentSessionResult(0, "done")


def _patch_launch_env(monkeypatch: pytest.MonkeyPatch, fake: _FakeAgent) -> None:
    monkeypatch.setattr(
        "coga.commands.launch._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga.commands.launch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    monkeypatch.setattr(
        "coga.commands.launch.spawn_agent_session", fake
    )


# --- baseline: chain works without git sync ------------------------------------


@pytest.fixture
def plain_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


def test_supervisor_respawns_next_step_after_bump(
    plain_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """launch -> agent bumps -> supervisor spawns a *second* agent for step 2.

    The regression guard for "restart is not working": the supervisor must
    respawn after the in-session bump rather than exit after one step.
    """
    slug = _create_agent_task(plain_repo, ["implement", "finish"])
    fake = _FakeAgent(plain_repo, actions=["bump", "mark_done"])
    _patch_launch_env(monkeypatch, fake)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output

    # Two sessions ran — the second is the respawn the supervisor performed
    # after the step-1 bump.
    assert fake.steps == ["1 (implement)", "2 (finish)"], fake.steps

    cfg = load_config(plain_repo)
    ticket = Ticket.read(list_tasks(cfg)[0].ticket_path)
    assert ticket.status == "done"


def test_supervisor_auto_restarts_through_three_steps(
    plain_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The core auto-restart regression: a 3-step workflow, one launch.

    One `coga launch` must drive the whole workflow: the agent completes a step
    with `coga bump`, the supervisor auto-restarts a fresh agent for the next,
    and so on through all three. Confirms the spawn/auto-restart-on-step-complete
    behavior and that the ticket is actually bumped 1 -> 2 -> 3 -> done.
    """
    slug = _create_agent_task(plain_repo, ["implement", "review", "finalize"])
    fake = _FakeAgent(plain_repo, actions=["bump", "bump", "mark_done"])
    _patch_launch_env(monkeypatch, fake)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output

    # Three sessions ran — two auto-restarts after the step-1 and step-2 bumps.
    assert fake.steps == [
        "1 (implement)",
        "2 (review)",
        "3 (finalize)",
    ], fake.steps

    cfg = load_config(plain_repo)
    ticket = Ticket.read(list_tasks(cfg)[0].ticket_path)
    assert ticket.status == "done"

    # The bumps really landed: the audit log records each auto-restart advance
    # (step 1 is the seeded starting step, so only 2 and 3 are "advanced to").
    log = (plain_repo / "log.md").read_text()
    assert "advanced to step 2 (review)" in log
    assert "advanced to step 3 (finalize)" in log


# --- functional: the supervisor really spawns an agent process ----------------
#
# The tests above stub `spawn_agent_session`. This one does not: it points the
# `claude` CLI at a real executable fake-agent script and lets the supervisor
# actually spawn it (compose prompt -> build argv -> run_with_done_marker, which
# falls back to `subprocess.run` with no TTY -> real child process). The fake
# agent shells out to `coga bump` / `coga mark done` exactly like a real agent's
# last action, then exits. So the whole spawn -> agent-exits -> re-read ->
# respawn loop runs end-to-end across three steps with nothing mocked but the
# TTY entry-gate.

_FAKE_AGENT = """\
#!{python}
import os, subprocess, sys

# Record which step this session ran on (the supervisor sets this per spawn).
with open(os.environ["COGA_FAKE_LOG"], "a") as fh:
    fh.write(os.environ.get({step_env!r}, "") + "\\n")

slug = os.environ["COGA_FAKE_SLUG"]
coga_os = os.environ["COGA_FAKE_COGA_OS"]

def coga(*args):
    return subprocess.run(
        [sys.executable, "-m", "coga.cli", *args], cwd=coga_os
    ).returncode

# A real agent's final action: bump on completion; on the last step bump fails
# (nothing to advance to) so finish the task instead.
if coga("bump", slug) != 0:
    coga("mark", "done", slug)
"""


def _install_fake_agent(coga_os: Path, tmp_path: Path) -> Path:
    script = tmp_path / "fake_agent.py"
    script.write_text(
        _FAKE_AGENT.format(python=sys.executable, step_env=EXPECTED_STEP_ENV)
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    # Point the claude CLI at the fake agent.
    toml = coga_os / "coga.toml"
    toml.write_text(toml.read_text().replace('cli = "claude"', f'cli = "{script}"'))
    return script


def test_launch_functionally_auto_restarts_through_three_steps(
    plain_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: one `coga launch` spawns a real agent per step, and the
    supervisor auto-restarts a fresh agent process after each `coga bump`.

    Nothing in the spawn/respawn path is mocked — the supervisor spawns the
    fake-agent executable for real, it runs `coga bump` in a child process, and
    the loop respawns for the next step. Confirms spawn/auto-restart across a
    3-step workflow drives the ticket 1 -> 2 -> 3 -> done.
    """
    slug = _create_agent_task(plain_repo, ["implement", "review", "finalize"])
    _install_fake_agent(plain_repo, tmp_path)
    fake_log = tmp_path / "sessions.log"

    # The spawned child inherits `os.environ` (build_launch_env copies it), so
    # hand the fake agent what it needs — and put the real `coga` package on its
    # path (the repo-root `coga/` OS dir otherwise shadows it as a namespace pkg).
    src_dir = Path(coga.__file__).resolve().parents[1]
    monkeypatch.setenv("PYTHONPATH", str(src_dir))
    monkeypatch.setenv("COGA_FAKE_SLUG", slug)
    monkeypatch.setenv("COGA_FAKE_COGA_OS", str(plain_repo))
    monkeypatch.setenv("COGA_FAKE_LOG", str(fake_log))
    # Only the TTY entry-gate is faked; the spawn itself is real.
    monkeypatch.setattr(
        "coga.commands.launch._interactive_stdio_has_tty", lambda: True
    )

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output

    # The supervisor spawned a real agent three times, one per step, in order.
    sessions = fake_log.read_text().split()
    assert sessions == [
        "1", "(implement)", "2", "(review)", "3", "(finalize)",
    ], fake_log.read_text()

    ticket = Ticket.read(list_tasks(load_config(plain_repo))[0].ticket_path)
    assert ticket.status == "done"


# --- the canary: same chain with real git sync in the loop --------------------


@pytest.fixture
def git_chain_repo(real_git, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Real git repo with a bare origin.

    Requesting `real_git` opts the whole test out of the autouse `_stub_git`
    no-op, so `coga.git.sync_*` runs for real against this repo — otherwise the
    sync-back we are probing would be stubbed to a no-op and the test
    would "lose work" as an artifact rather than a finding.
    """
    repo = init_git_repo(tmp_path)
    # Push-auth preflight shells out to git/gh; this test is about the chain,
    # not the auth gate, so no-op it.
    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth", lambda *a, **k: None
    )
    monkeypatch.chdir(repo.coga_os)
    return repo


def test_supervisor_respawns_next_step_after_bump_with_real_git(
    git_chain_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The chain must survive real git sync without losing work.

    This asserts both that the respawn happens (restart) and that the finished
    `done` state is present in the launch checkout at the end.
    """
    slug = _create_agent_task(git_chain_repo.coga_os, ["implement", "finish"])
    git_chain_repo.git("add", "-A")
    git_chain_repo.git("commit", "-m", "seed chain task")

    fake = _FakeAgent(git_chain_repo.coga_os, actions=["bump", "mark_done"])
    _patch_launch_env(monkeypatch, fake)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output

    # Respawn happened.
    assert fake.steps == ["1 (implement)", "2 (finish)"], fake.steps

    primary_ticket = Ticket.read(
        list_tasks(load_config(git_chain_repo.coga_os))[0].ticket_path
    )
    assert primary_ticket.status == "done", (
        "the finished ticket did not survive the chain — work lost"
    )


def test_session_survives_concurrent_control_branch_advance(
    git_chain_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Does a session lose work when the control branch advances underneath it?

    The realistic trigger for "losing work" / "restart is not working": while a
    session runs, ANOTHER coga instance (or any commit) lands on `origin/main`.
    The session's sync must then land on a moved control branch
    (non-fast-forward) instead of a clean fast-forward. If that land is
    dropped, the finished `done` state never reaches the control branch and a
    fresh `coga launch` elsewhere re-reads stale state — exactly the symptom.

    A rival commit is pushed to `origin/main` at the start of step 1, before the
    session's own bumps land.
    """
    slug = _create_agent_task(git_chain_repo.coga_os, ["implement", "finish"])
    git_chain_repo.git("add", "-A")
    git_chain_repo.git("commit", "-m", "seed chain task")
    git_chain_repo.git("push", "origin", "main")

    def advance_main_once(step_index: int) -> None:
        if step_index == 1:
            git_chain_repo.push_competing_commit(
                "coga/tasks/rival/ticket.md", "rival instance\n"
            )

    fake = _FakeAgent(
        git_chain_repo.coga_os, actions=["bump", "mark_done"], hook=advance_main_once
    )
    _patch_launch_env(monkeypatch, fake)

    result = CliRunner().invoke(app, ["launch", slug])
    assert result.exit_code == 0, result.output
    assert fake.steps == ["1 (implement)", "2 (finish)"], fake.steps

    primary_ticket = Ticket.read(
        list_tasks(load_config(git_chain_repo.coga_os))[0].ticket_path
    )
    assert primary_ticket.status == "done", (
        "control branch advanced mid-session and the finished state "
        "was not synced — work lost"
    )
