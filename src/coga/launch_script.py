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
from coga.bump import OperatorResolutionError, resolve_operator
from coga.config import Config, build_launch_env, load_config
from coga.logfile import append_log
from coga.lifecycle import TERMINAL_STATUSES
from coga.notification import post, preflight_post
from coga.repl_supervisor import (
    ASSIST_AGENT_ENV,
    ASSIST_BRANCH_ENV,
    ASSIST_PR_ENV,
    EXPECTED_STEP_ENV,
    EXPECTED_TASK_ENV,
    SENTINEL_ENV,
)
from coga.task_env import SCRIPT_TASK_ENV, apply_task_env, host_repo_root
from coga.tasks import (
    BootstrapRef,
    TargetRef,
    TaskNotFoundError,
    TaskRef,
    read_ticket,
    resolve_target,
)
from coga.ticket import Ticket, TicketError


SCRIPT_ENTRY_POINT = "ticket.py"


@dataclass(frozen=True)
class ScriptPhaseResult:
    """The child exit and task state observed after one deterministic phase."""

    exit_code: int
    ticket: Ticket | None
    ran: bool = True
    cfg: Config | None = None
    ref: TargetRef | None = None


class ScriptChainResult(NamedTuple):
    """Result of consecutive deterministic steps before an agent handoff."""

    exit_code: int
    ticket: Ticket | None
    needs_agent: bool
    stop_reason: str | None
    cfg: Config | None = None
    ref: TargetRef | None = None


class ScriptPublicationError(RuntimeError):
    """A recorded-assist script launch is missing part of its assist identity."""


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
    assist_branch: str | None = None,
    assist_agent: str | None = None,
    assist_pr_url: str | None = None,
    failure_important: bool = False,
) -> ScriptPhaseResult:
    """Run one target-owned deterministic phase without composing a prompt.

    Secrets and task identity are preflighted before the stateful
    ``active -> in_progress`` transition.  The child receives no operands and
    runs from the host repository root under Coga's current Python
    interpreter.  The launcher, never this helper, decides whether an agent
    phase follows.

    A recorded human-step assist (`assist_branch` and friends) runs the same
    phase; the child additionally inherits the assist identity so its
    lifecycle commands name the assisting agent, and its ticket result is
    published to control right after it exits.
    """

    strict_assist = assist_branch is not None
    if strict_assist and (not assist_agent or not assist_pr_url):
        raise ScriptPublicationError(
            "recorded-assist script launch is missing its agent or PR"
        )

    entry = script_entry_point(ref)
    if entry is None:
        # Classification is a point-in-time observation. Activation, a prior
        # deterministic phase, or another checkout may have removed the fixed
        # entry before this phase began. Reclassify as agent-only instead of
        # turning the stale stat into a launch failure.
        return ScriptPhaseResult(
            exit_code=0,
            ticket=ticket,
            ran=False,
            cfg=cfg,
            ref=ref,
        )

    # Resolve every declared secret before publishing a started lifecycle.
    env = build_launch_env(cfg, ticket.secrets)
    if strict_assist:
        try:
            preflight_post(cfg)
        except typer.Exit as exc:
            raise ScriptPublicationError(
                "the recorded assist cannot run ticket.py until its live "
                "notification configuration is valid"
            ) from exc

    if not stateless and not isinstance(ref, TaskRef):
        raise ValueError(
            f"Stateful script phase requires a task target, got {ref.id_slug}."
        )

    if strict_assist and ticket.status != "in_progress":
        raise ScriptPublicationError(
            "recorded-assist lifecycle was not published before ticket.py"
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

    if not stateless:
        append_log(cfg, ref.id_slug, "system", "launched as a script (ticket.py)")
        # Publish the launch line before user code runs.
        git.sync_log(cfg, message=f"Log: {ref.id_slug}")

    pre_sync_identity = _routing_identity(ticket)

    # The lifecycle and launch-log syncs above may fetch/rebase a control
    # checkout. Re-derive every input after that last moving boundary: a peer
    # may have replaced or removed ticket.py, changed coga.toml, edited the
    # ticket, or changed its secret declarations. A vanished entry point is a
    # fresh agent-only classification, not a failed execution of a stale path.
    cfg = load_config(cfg.repo_root)
    try:
        refreshed_ref = resolve_target(cfg, ref.id_slug)
    except TaskNotFoundError:
        return ScriptPhaseResult(
            exit_code=0,
            ticket=None,
            ran=False,
            cfg=cfg,
            ref=ref,
        )
    if refreshed_ref.id_slug != ref.id_slug:
        raise FileNotFoundError(
            f"Selected task {ref.id_slug!r} disappeared while preparing "
            "ticket.py."
        )
    ref = refreshed_ref
    ticket = read_ticket(ref)
    entry = script_entry_point(ref)
    if entry is None:
        return ScriptPhaseResult(
            exit_code=0,
            ticket=ticket,
            ran=False,
            cfg=cfg,
            ref=ref,
        )

    if not stateless and (
        ticket.status != "in_progress"
        or _routing_identity(ticket) != pre_sync_identity
    ):
        # The moving sync above is authoritative. A peer may have closed or
        # parked the task, advanced it to a configured agent after a human
        # assist, handed it to a human, changed its owner, or changed its
        # main-agent choice — any of which reroutes the next phase. Do not
        # execute code selected from the stale pre-sync lifecycle; let the chain
        # classify the fresh state.
        return ScriptPhaseResult(
            exit_code=0,
            ticket=ticket,
            ran=False,
            cfg=cfg,
            ref=ref,
        )

    env = build_launch_env(cfg, ticket.secrets)
    env = apply_task_env(env, cfg, ref, ticket)
    # A normal ticket script must not inherit ownership witnesses from an outer
    # agent session. A strict human assist re-mints only the narrow task and PR
    # capability needed by in-script lifecycle operations. Clear the sentinel
    # itself too: lifecycle writers signal it even outside supervised sessions.
    # Script attribution is separate from both ownership and publication.
    env.pop("COGA_SUPERVISED", None)
    env.pop(SENTINEL_ENV, None)
    env.pop(EXPECTED_TASK_ENV, None)
    env.pop(EXPECTED_STEP_ENV, None)
    env[SCRIPT_TASK_ENV] = str(ref.path.resolve())
    if strict_assist:
        env[EXPECTED_TASK_ENV] = str(ref.path.resolve())
        env[EXPECTED_STEP_ENV] = ticket.step or ""
        env[ASSIST_AGENT_ENV] = assist_agent or ""
        env[ASSIST_BRANCH_ENV] = assist_branch or ""
        env[ASSIST_PR_ENV] = assist_pr_url or ""

    completed = subprocess.run(
        [sys.executable, str(entry)],
        cwd=host_repo_root(cfg),
        env=env,
        check=False,
    )
    exit_code = completed.returncode

    after: Ticket | None = None
    ticket_read_error: Exception | None = None
    if ref.ticket_path.exists():
        try:
            after = Ticket.read(ref.ticket_path)
        except (OSError, UnicodeError, TicketError) as exc:
            ticket_read_error = exc
    if not stateless:
        # The audit belongs to the launch, not to the continued existence or
        # parseability of ticket.md. Record it even when user code deleted or
        # malformed its own ticket, and never let that reread replace a
        # non-zero child result.
        append_log(
            cfg,
            ref.id_slug,
            "system",
            f"script exited with code {exit_code}",
        )
        if strict_assist:
            # The assist session ends with this phase's result, so publish it
            # now rather than waiting for the end-of-command sweep.
            git.sync_task_state(
                cfg, ref.path, message=f"Ticket: {ref.id_slug} — script result"
            )

    if exit_code != 0 and not stateless:
        observed = after or ticket
        current = observed.current_step()
        where = (
            f" at step {observed.step_index()} ({current['name']})"
            if current is not None
            else ""
        )
        try:
            post(
                cfg,
                f"💥 script failed on *{ref.id_slug}* "
                f"\"{observed.title}\": exit {exit_code}{where}",
                task_path=ref.path,
                owner=observed.owner or cfg.current_user,
                important=failure_important,
                # The deterministic failure and its exit code are already
                # durable; a notification outage must not replace that result.
                fatal=False,
            )
        except typer.Exit:
            if not strict_assist:
                raise
            # Configuration was preflighted before user code. If it changed
            # while ticket.py ran, keep the durable child exit authoritative.

    if exit_code == 0:
        if ticket_read_error is not None:
            raise ticket_read_error
        # User code and nested lifecycle syncs may change coga.toml or move the
        # checkout across a freshly integrated control tip. The caller uses
        # this result for handoff classification and agent setup, so return a
        # config, target, and ticket derived after the child boundary rather
        # than the objects captured before execution.
        cfg = load_config(cfg.repo_root)
        try:
            ref = resolve_target(cfg, ref.id_slug)
        except TaskNotFoundError:
            after = None
        else:
            after = read_ticket(ref)
        # A bootstrap script is a command implementation: preserve its stdout
        # for callers such as ``$(coga <verb>)`` by keeping framing on stderr.
        typer.echo(f"{ref.id_slug}: script ran successfully", err=stateless)

    return ScriptPhaseResult(
        exit_code=exit_code,
        ticket=after,
        cfg=cfg,
        ref=ref,
    )


def run_script_chain(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    ran_steps: set[str | None],
    *,
    assist_branch: str | None = None,
    assist_agent: str | None = None,
    assist_pr_url: str | None = None,
    failure_important: bool = False,
) -> ScriptChainResult:
    """Run ``ticket.py`` once per consecutive step until agent work remains."""

    stateless = isinstance(ref, BootstrapRef)
    current = ticket
    phase_assist_agent = assist_agent
    while current.step not in ran_steps:
        step_key = current.step
        ran_steps.add(step_key)
        _echo_script_iteration(cfg, ref, current, stateless=stateless)

        before = current
        phase = run_script_phase(
            cfg,
            ref,
            before,
            stateless=stateless,
            assist_branch=assist_branch,
            assist_agent=phase_assist_agent,
            assist_pr_url=assist_pr_url,
            failure_important=failure_important,
        )
        cfg = phase.cfg or cfg
        ref = phase.ref or ref
        if not phase.ran:
            ran_steps.discard(step_key)
            return _classify_script_handoff(
                cfg,
                ref,
                phase.ticket,
                stateless=stateless,
                strict_assist=assist_branch is not None,
            )
        if phase.exit_code != 0:
            return ScriptChainResult(
                phase.exit_code,
                phase.ticket,
                False,
                None,
                cfg,
                ref,
            )

        after = phase.ticket
        if stateless:
            return ScriptChainResult(0, after, False, None, cfg, ref)
        if after is None:
            return ScriptChainResult(
                0,
                None,
                False,
                "Launch: task directory removed by script — nothing to chain",
                cfg,
                ref,
            )
        if after.status != "in_progress":
            if after.status in TERMINAL_STATUSES:
                reason = f"{ref.id_slug}: task is {after.status}"
            elif after.status == "paused":
                reason = f"{ref.id_slug}: task is paused"
            else:
                reason = f"{ref.id_slug}: task status is {after.status!r}"
            return ScriptChainResult(0, after, False, reason, cfg, ref)

        # An unchanged step is the completion-contract signal for row three:
        # deterministic preparation succeeded and the agent continues that
        # same open unit of work. A changed step gets its own deterministic
        # phase before any agent preflight or prompt composition, unless the
        # workflow handed control to the owner. The deterministic chain must
        # honor the same approval boundary as the agent supervisor instead of
        # running ticket.py on somebody else's turn.
        if after.step == before.step:
            return ScriptChainResult(0, after, True, None, cfg, ref)
        try:
            operator = resolve_operator(cfg, ref, after)
        except OperatorResolutionError as exc:
            return ScriptChainResult(
                0, after, False, f"{ref.id_slug}: {exc}; stopping", cfg, ref
            )
        if operator is None or operator.is_human:
            who = "nobody" if operator is None else operator.name
            return ScriptChainResult(
                0,
                after,
                False,
                f"{ref.id_slug}: next step hands off to {who}; "
                "returning to caller",
                cfg,
                ref,
            )
        if assist_branch is not None:
            # The override authorizes the human-held phase only. Once a
            # deterministic bump hands control to an agent step, each chained
            # script uses that step's derived agent for its assist publication
            # capability. Deterministic completion still credits system.
            phase_assist_agent = operator.name
        current = after

    return ScriptChainResult(0, current, True, None, cfg, ref)


def _classify_script_handoff(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket | None,
    *,
    stateless: bool,
    strict_assist: bool,
) -> ScriptChainResult:
    """Classify fresh state after a formerly-scripted phase no longer runs."""
    if stateless:
        return ScriptChainResult(0, ticket, True, None, cfg, ref)
    if ticket is None:
        return ScriptChainResult(
            0,
            None,
            False,
            "Launch: task directory removed before script — nothing to chain",
            cfg,
            ref,
        )
    if ticket.status not in {"active", "in_progress"}:
        if ticket.status in TERMINAL_STATUSES:
            reason = f"{ref.id_slug}: task is {ticket.status}"
        elif ticket.status == "paused":
            reason = f"{ref.id_slug}: task is paused"
        else:
            reason = f"{ref.id_slug}: task status is {ticket.status!r}"
        return ScriptChainResult(0, ticket, False, reason, cfg, ref)
    try:
        operator = resolve_operator(cfg, ref, ticket)
    except OperatorResolutionError as exc:
        return ScriptChainResult(
            0, ticket, False, f"{ref.id_slug}: {exc}; stopping", cfg, ref
        )
    if operator is None:
        return ScriptChainResult(
            0,
            ticket,
            False,
            f"{ref.id_slug}: next step has no operator; returning to caller",
            cfg,
            ref,
        )
    # A strict assist is already authorized to run one session on an
    # owner-held step, so it does not stop here.
    if operator.is_human and not strict_assist:
        return ScriptChainResult(
            0,
            ticket,
            False,
            f"{ref.id_slug}: next step hands off to {operator.name}; "
            "returning to caller",
            cfg,
            ref,
        )
    return ScriptChainResult(0, ticket, True, None, cfg, ref)


def _routing_identity(ticket: Ticket) -> tuple[object, ...]:
    """The persisted inputs that decide who holds a ticket, plus its status.

    Compared across the moving syncs above: a peer edit to any of them
    reroutes the next phase, so the pre-sync classification must not run.
    """
    workflow = ticket.workflow
    steps = workflow.get("steps") if isinstance(workflow, dict) else None
    roles = tuple(
        (step.get("assignee") if isinstance(step, dict) else step)
        for step in (steps if isinstance(steps, list) else [])
    )
    return (ticket.status, ticket.step, ticket.owner, ticket.agent, roles)


def _echo_script_iteration(
    cfg: Config,
    ref: TargetRef,
    ticket: Ticket,
    *,
    stateless: bool,
) -> None:
    if stateless:
        typer.echo(f"→ running {ref.id_slug} ticket.py", err=True)
        return
    current = ticket.current_step()
    try:
        operator = resolve_operator(
            cfg, ref, ticket, allow_prospective_default=True
        )
        who = operator.name if operator is not None else "none"
    except OperatorResolutionError:
        who = "unresolved"
    if current is None:
        typer.echo(
            f"→ running {ref.id_slug} ticket.py "
            f"(status={ticket.status}, operator={who})"
        )
        return
    typer.echo(
        f"→ entering step {ticket.step}: {current['name']} "
        f"(status={ticket.status}, operator={who})"
    )


__all__ = [
    "SCRIPT_ENTRY_POINT",
    "ScriptChainResult",
    "ScriptPhaseResult",
    "ScriptPublicationError",
    "run_script_chain",
    "run_script_phase",
    "script_entry_point",
]
