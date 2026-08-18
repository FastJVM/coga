"""Deterministic ``ticket.py`` launch phase.

A directory-form ticket owns a deterministic half when ``ticket.py`` sits
beside ``ticket.md``.  The fixed name is the whole classifier: Coga does not
scan for plugins, import ticket code, or consult frontmatter to select a mode.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import typer

from coga import git
from coga.config import Config, build_launch_env
from coga.logfile import append_log
from coga.lifecycle import TERMINAL_STATUSES
from coga.notification import post
from coga.repl_supervisor import EXPECTED_STEP_ENV, EXPECTED_TASK_ENV
from coga.task_env import apply_task_env, host_repo_root
from coga.tasks import BootstrapRef, TargetRef, TaskRef
from coga.ticket import Ticket


SCRIPT_ENTRY_POINT = "ticket.py"


@dataclass(frozen=True)
class ScriptPhaseResult:
    """The child exit and task state observed after one deterministic phase."""

    exit_code: int
    ticket: Ticket | None


class ScriptChainResult(NamedTuple):
    """Result of consecutive deterministic steps before an agent handoff."""

    exit_code: int
    ticket: Ticket | None
    needs_agent: bool
    stop_reason: str | None


def script_entry_point(ref: TargetRef) -> Path | None:
    """Return the target's fixed script entry point when it is a regular file.

    File-form tasks have no companion directory and therefore cannot carry a
    deterministic half.  Directory-form tasks and bootstrap tickets both use
    the one reserved sibling name; executable bits and other filenames do not
    participate in dispatch.
    """

    task_dir = ref.task_dir
    if task_dir is None:
        return None
    candidate = task_dir / SCRIPT_ENTRY_POINT
    return candidate if candidate.is_file() else None


def run_script_phase(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    *,
    stateless: bool,
) -> ScriptPhaseResult:
    """Run one target-owned deterministic phase without composing a prompt.

    Secrets and task identity are preflighted before the stateful
    ``active -> in_progress`` transition.  The child receives no operands and
    runs from the host repository root under Coga's current Python
    interpreter.  The launcher, never this helper, decides whether an agent
    phase follows.
    """

    entry = script_entry_point(ref)
    if entry is None:
        raise FileNotFoundError(
            f"Script entry point not found for {ref.id_slug}: "
            f"expected {ref.task_dir / SCRIPT_ENTRY_POINT if ref.task_dir else SCRIPT_ENTRY_POINT}"
        )

    # Resolve every declared secret before publishing a started lifecycle.
    env = build_launch_env(cfg, ticket.secrets)

    if not stateless and not isinstance(ref, TaskRef):
        raise ValueError(
            f"Stateful script phase requires a task target, got {ref.id_slug}."
        )

    if not stateless and ticket.status == "active":
        # Local import keeps the pure classifier importable by coga.validate;
        # coga.mark itself imports the validator for transition checks.
        from coga.mark import mark_in_progress

        current = ticket.current_step()
        step_note = (
            f" (step {ticket.step_index()}: {current['name']})"
            if current is not None
            else ""
        )
        mark_in_progress(
            cfg,
            ref,
            ticket,
            actor="system",
            log_message="started (active → in_progress) via coga launch",
            slack_text=(
                f"▶️ script started *{ref.id_slug}* "
                f"\"{ticket.title}\"{step_note}"
            ),
            echo=f"{ref.id_slug}: in_progress",
        )

    env = apply_task_env(env, cfg, ref, ticket)
    # These witnesses authorize one composed agent step.  A ticket script is
    # launched directly and must not inherit them from an outer agent session.
    env.pop("COGA_SUPERVISED", None)
    env.pop(EXPECTED_TASK_ENV, None)
    env.pop(EXPECTED_STEP_ENV, None)

    if not stateless:
        append_log(cfg, ref.id_slug, "system", "launched as a script (ticket.py)")
        # Commit the launch line before user code runs: an entry point may
        # switch branches, and a dirty tracked log would make git refuse it.
        git.sync_log(cfg, message=f"Log: {ref.id_slug}")

    completed = subprocess.run(
        [sys.executable, str(entry)],
        cwd=host_repo_root(cfg),
        env=env,
        check=False,
    )
    exit_code = completed.returncode

    after: Ticket | None = None
    if ref.ticket_path.exists():
        after = Ticket.read(ref.ticket_path)
        if not stateless:
            append_log(
                cfg,
                ref.id_slug,
                "system",
                f"script exited with code {exit_code}",
            )

    if exit_code != 0 and not stateless:
        observed = after or ticket
        current = observed.current_step()
        where = (
            f" at step {observed.step_index()} ({current['name']})"
            if current is not None
            else ""
        )
        post(
            cfg,
            f"💥 script failed on *{ref.id_slug}* "
            f"\"{observed.title}\": exit {exit_code}{where}",
            task_path=ref.path,
            owner=observed.owner or cfg.current_user,
            watchers=observed.watchers,
            # The deterministic failure and its exit code are already durable;
            # a notification outage must not replace that result.
            fatal=False,
        )

    if exit_code == 0:
        # A bootstrap script is a command implementation: preserve its stdout
        # for callers such as ``$(coga <verb>)`` by keeping framing on stderr.
        typer.echo(f"{ref.id_slug}: script ran successfully", err=stateless)

    return ScriptPhaseResult(exit_code=exit_code, ticket=after)


def run_script_chain(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    ran_steps: set[str | None],
) -> ScriptChainResult:
    """Run ``ticket.py`` once per consecutive step until agent work remains."""

    stateless = isinstance(ref, BootstrapRef)
    current = ticket
    while current.step not in ran_steps:
        step_key = current.step
        ran_steps.add(step_key)
        _echo_script_iteration(ref, current, stateless=stateless)

        before = current
        phase = run_script_phase(
            cfg,
            ref,
            before,
            stateless=stateless,
        )
        if phase.exit_code != 0:
            return ScriptChainResult(
                phase.exit_code,
                phase.ticket,
                False,
                None,
            )

        after = phase.ticket
        if stateless:
            return ScriptChainResult(0, after, False, None)
        if after is None:
            return ScriptChainResult(
                0,
                None,
                False,
                "Launch: task directory removed by script — nothing to chain",
            )
        if after.status != "in_progress":
            if after.status in TERMINAL_STATUSES:
                reason = f"{ref.id_slug}: task is {after.status}"
            elif after.status == "paused":
                reason = f"{ref.id_slug}: task is paused"
            else:
                reason = f"{ref.id_slug}: task status is {after.status!r}"
            return ScriptChainResult(0, after, False, reason)

        # An unchanged step is the completion-contract signal for row three:
        # deterministic preparation succeeded and the agent continues that
        # same open unit of work. A changed step gets its own deterministic
        # phase before any agent preflight or prompt composition.
        if after.step == before.step:
            return ScriptChainResult(0, after, True, None)
        current = after

    return ScriptChainResult(0, current, True, None)


def _echo_script_iteration(
    ref: TargetRef,
    ticket: Ticket,
    *,
    stateless: bool,
) -> None:
    if stateless:
        typer.echo(f"→ running {ref.id_slug} ticket.py", err=True)
        return
    current = ticket.current_step()
    if current is None:
        typer.echo(
            f"→ running {ref.id_slug} ticket.py "
            f"(status={ticket.status}, assignee={ticket.assignee or 'unassigned'})"
        )
        return
    typer.echo(
        f"→ entering step {ticket.step}: {current['name']} "
        f"(status={ticket.status}, assignee={ticket.assignee or 'unassigned'})"
    )


__all__ = [
    "SCRIPT_ENTRY_POINT",
    "ScriptChainResult",
    "ScriptPhaseResult",
    "run_script_chain",
    "run_script_phase",
    "script_entry_point",
]
