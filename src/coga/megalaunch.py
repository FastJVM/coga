"""Sequential console launcher for active, agent-owned Coga work.

Megalaunch is a set of normal interactive launches, not a headless drain: each
eligible step spawns the agent REPL under the PTY watcher exactly like
`coga launch`, so output streams live to the console and the done-sentinel
(`coga bump` / `mark done` / `block`) tears the REPL down and hands control
back to the sweep. Recurring's idle-timeout / max-session backstops are armed
so one wedged agent can't starve the rest of the queue. Because the spawned
REPLs are interactive, the whole run requires a TTY — fail loud otherwise.

Tasks are serviced oldest-first (first `coga/log.md` line per ref — committed
content, so the order survives clones where file mtimes don't). The budget
guard reads each agent's own subscription usage windows via
`coga.usage_probe` — the 5h/session window plus the weekly window, re-probed
before every launch — instead of coga summing its own token records. An agent
whose windows can't be read is skipped conservatively, never launched blind.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from coga import usage_probe
from coga.blackboard import open_blockers
from coga.commands.launch import (
    _interactive_stdio_has_tty,
    _skip_permissions_argv_for_launch,
    spawn_agent_session,
)
from coga.commands.launch_script import is_script_launch
from coga.commands.recurring import (
    _recurring_idle_timeout,
    _recurring_max_session,
)
from coga.compose import ComposeError, compose_prompt
from coga.config import Config, ConfigError, SecretError, build_launch_env, load_config
from coga.github_preflight import check_git_auth, check_git_remote
from coga.logfile import first_activity_map
from coga.mark import mark_in_progress
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import TaskRef, list_tasks, read_ticket
from coga.ticket import Ticket, TicketError
from coga.validate import TaskValidationError


class MegalaunchError(Exception):
    """Megalaunch cannot run at all — e.g. no TTY for the interactive REPLs."""


MegalaunchOutcome = Literal[
    "completed",
    "blocked",
    "skipped-human-gate",
    "skipped-unresolved-blocker",
    "skipped-budget",
    "failed",
]


@dataclass(frozen=True)
class MegalaunchResult:
    slug: str
    outcome: MegalaunchOutcome
    detail: str
    agent: str | None = None
    launched: bool = False
    budget: usage_probe.BudgetDecision | None = None


@dataclass(frozen=True)
class MegalaunchRun:
    started_at: datetime
    results: list[MegalaunchResult] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        counts = {
            "launched": sum(1 for result in self.results if result.launched),
            "completed": 0,
            "blocked": 0,
            "skipped-human-gate": 0,
            "skipped-unresolved-blocker": 0,
            "skipped-budget": 0,
            "failed": 0,
        }
        for result in self.results:
            counts[result.outcome] += 1
        return counts


def run_megalaunch(
    cfg: Config | None = None,
    *,
    max_tasks: int | None = None,
    max_steps_per_task: int = 8,
    probes: dict[str, usage_probe.UsageProbe] | None = None,
) -> MegalaunchRun:
    """Attempt active, launchable tasks sequentially with one budget guard."""
    cfg = cfg or load_config()
    if not _interactive_stdio_has_tty():
        raise MegalaunchError(
            "megalaunch spawns interactive agent REPLs and requires a TTY "
            "(stdin and stdout must both be terminals). Run it from a real "
            "shell."
        )
    started_at = datetime.now(timezone.utc)
    results: list[MegalaunchResult] = []
    attempted = 0
    # Liveness backstops for the spawned REPLs, resolved once per sweep with
    # the same precedence recurring uses (env override > [launch] config >
    # default). Human keystrokes count as activity, so an attended session
    # is only torn down when it is genuinely idle.
    idle_timeout = _recurring_idle_timeout(cfg)
    max_session = _recurring_max_session(cfg)
    # One probe per configured agent for the whole run; each budget check
    # re-reads through it, so a launch's spend shows up in the next decision.
    if probes is None:
        probes = usage_probe.build_probes(cfg)

    for ref in _tasks_oldest_first(cfg):
        if max_tasks is not None and attempted >= max_tasks:
            break
        try:
            ticket = read_ticket(ref)
        except TicketError as exc:
            results.append(_result(ref, "failed", f"unreadable ticket: {exc}"))
            continue

        # Only `active` (launchable) and `blocked` (reportable) tickets are in
        # scope. draft/paused/done/in_progress are ignored — never launched and
        # never counted as a result.
        if ticket.status not in {"active", "blocked"}:
            continue

        candidate = _candidate_result(cfg, ref, ticket, probes)
        if candidate is not None:
            results.append(candidate)
            continue

        attempted += 1
        results.append(
            _launch_until_stop(
                cfg,
                ref,
                ticket,
                probes,
                max_steps_per_task=max_steps_per_task,
                idle_timeout=idle_timeout,
                max_session=max_session,
            )
        )

    return MegalaunchRun(started_at=started_at, results=results)


def _tasks_oldest_first(cfg: Config) -> list[TaskRef]:
    """All tasks, oldest creation first (first `coga/log.md` line per ref).

    The first log line is the draft/create entry — committed content, so the
    ordering survives clone/checkout where file mtimes collapse to "all
    equal". Refs with no parseable log line sort last, stable by slug.
    """
    created = first_activity_map(cfg)

    def key(ref: TaskRef) -> tuple[bool, datetime, str]:
        ts = created.get(ref.id_slug)
        return (ts is None, ts or datetime.min, ref.id_slug)

    return sorted(list_tasks(cfg), key=key)


def _candidate_result(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    probes: dict[str, usage_probe.UsageProbe],
) -> MegalaunchResult | None:
    blockers = open_blockers(ref.ticket_path)
    if ticket.status == "blocked":
        detail = "; ".join(blocker.reason for blocker in blockers) or "status is blocked"
        return _result(ref, "skipped-unresolved-blocker", detail, ticket.assignee)

    if ticket.status != "active":
        return None
    if blockers:
        detail = "; ".join(blocker.reason for blocker in blockers)
        return _result(ref, "skipped-unresolved-blocker", detail, ticket.assignee)

    current = ticket.current_step()
    if current is None:
        return _result(ref, "skipped-human-gate", "no current workflow step", ticket.assignee)
    if ticket.assignee not in cfg.agents:
        return _result(
            ref,
            "skipped-human-gate",
            f"assignee {ticket.assignee or 'unassigned'} is not a configured agent",
            ticket.assignee,
        )
    if is_script_launch(cfg, ticket):
        return _result(
            ref,
            "skipped-human-gate",
            "current step is script-backed; recurring/script launch owns it",
            ticket.assignee,
        )

    budget = usage_probe.check_budget(probes, ticket.assignee, cfg.megalaunch)
    if not budget.allowed:
        return _result(
            ref,
            "skipped-budget",
            budget.detail,
            ticket.assignee,
            budget=budget,
        )
    return None


def _launch_until_stop(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    probes: dict[str, usage_probe.UsageProbe],
    *,
    max_steps_per_task: int,
    idle_timeout: float | None = None,
    max_session: float | None = None,
) -> MegalaunchResult:
    launched = False
    last_budget: usage_probe.BudgetDecision | None = None
    step_count = 0

    while True:
        step_count += 1
        if step_count > max_steps_per_task:
            return _result(
                ref,
                "failed",
                f"exceeded {max_steps_per_task} unattended steps",
                ticket.assignee,
                launched=launched,
                budget=last_budget,
            )

        if ticket.assignee not in cfg.agents:
            return _result(
                ref,
                "completed",
                f"handed off to {ticket.assignee or 'unassigned'}",
                ticket.assignee,
                launched=launched,
                budget=last_budget,
            )

        # Re-probe before every launch — the previous step just spent budget,
        # and the agent's own usage window is the only accounting we trust.
        budget = usage_probe.check_budget(probes, ticket.assignee, cfg.megalaunch)
        last_budget = budget
        if not budget.allowed:
            return _result(
                ref,
                "skipped-budget",
                budget.detail,
                ticket.assignee,
                launched=launched,
                budget=budget,
            )

        preflight = _preflight_agent_launch(cfg, ref, ticket)
        if preflight is not None:
            return _result(
                ref,
                "failed",
                preflight,
                ticket.assignee,
                launched=launched,
                budget=budget,
            )

        if ticket.status == "active":
            try:
                mark_in_progress(
                    cfg,
                    ref,
                    ticket,
                    actor="megalaunch",
                    log_message="started (active → in_progress) via coga megalaunch",
                    echo=None,
                )
            except TaskValidationError as exc:
                return _result(ref, "failed", str(exc), ticket.assignee, budget=budget)

        before = read_ticket(ref)
        try:
            agent = cfg.agent_type(before.assignee or "")
            env = build_launch_env(cfg, before.secrets)
            env["COGA_SUPERVISED"] = "1"
            # A normal interactive launch: the REPL streams to the console
            # under the PTY watcher, and the done-sentinel (`coga bump` /
            # `mark done` / `block`) releases it — never headless `-p`, which
            # buffers all output until the run ends.
            session = spawn_agent_session(
                cfg,
                ref,
                before,
                agent,
                "interactive",
                env=env,
                actor="megalaunch",
                log_message="launched via coga megalaunch",
                autonomy_override="interactive",
                name=before.title or "",
                skip_permissions_argv=_skip_permissions_argv_for_launch(
                    agent, "interactive", ref
                ),
                idle_timeout=idle_timeout,
                max_session=max_session,
                label="Megalaunch",
                warn_blackboard=True,
                capture_usage=True,
            )
        except (ComposeError, ConfigError, SecretError) as exc:
            return _result(ref, "failed", str(exc), before.assignee, budget=budget)
        except FileNotFoundError:
            return _result(
                ref,
                "failed",
                f"agent CLI {agent.cli!r} not found",
                before.assignee,
                budget=budget,
            )

        launched = True
        after = read_ticket(ref)
        if after.status == "blocked":
            blockers = open_blockers(ref.ticket_path)
            detail = "; ".join(blocker.reason for blocker in blockers) or "blocked"
            return _result(ref, "blocked", detail, after.assignee, launched=True, budget=budget)
        if session.termination_kind == "timeout":
            return _result(
                ref,
                "failed",
                "agent hit the liveness limit (idle/max-session) without "
                "signalling done",
                after.assignee,
                launched=True,
                budget=budget,
            )
        if session.exit_code != 0:
            return _result(
                ref,
                "failed",
                f"agent exited with code {session.exit_code}",
                after.assignee,
                launched=True,
                budget=budget,
            )
        if after.status == "done":
            return _result(ref, "completed", "task done", after.assignee, launched=True, budget=budget)
        if after.status != "in_progress":
            return _result(
                ref,
                "completed",
                f"status is {after.status}",
                after.assignee,
                launched=True,
                budget=budget,
            )
        if after.assignee not in cfg.agents:
            return _result(
                ref,
                "completed",
                f"handed off to {after.assignee or 'unassigned'}",
                after.assignee,
                launched=True,
                budget=budget,
            )
        if (after.step, after.status) == (before.step, before.status):
            return _result(
                ref,
                "failed",
                "agent exited without changing task state",
                after.assignee,
                launched=True,
                budget=budget,
            )
        ticket = after


def _preflight_agent_launch(cfg: Config, ref: TaskRef, ticket: Ticket) -> str | None:
    try:
        agent = cfg.agent_type(ticket.assignee or "")
    except ConfigError as exc:
        return str(exc)
    if ticket.status not in {"active", "in_progress"}:
        return f"status is {ticket.status}; expected active or in_progress"
    if shutil.which(agent.cli) is None:
        return f"agent CLI {agent.cli!r} not found in PATH"
    try:
        _skip_permissions_argv_for_launch(agent, "interactive", ref)
        compose_prompt(cfg, ref, ticket, autonomy_override="interactive")
        build_launch_env(cfg, ticket.secrets)
    except (ConfigError, ComposeError, SecretError) as exc:
        return str(exc)
    if cfg.git_enabled and check_git_remote(cfg.git_remote).ok:
        auth = check_git_auth(cfg.git_remote)
        if not auth.ok:
            return f"git push access unavailable: {auth.detail}"
    return None


def _result(
    ref: TaskRef,
    outcome: MegalaunchOutcome,
    detail: str,
    agent: str | None = None,
    *,
    launched: bool = False,
    budget: usage_probe.BudgetDecision | None = None,
) -> MegalaunchResult:
    return MegalaunchResult(
        slug=ref.id_slug,
        outcome=outcome,
        detail=detail,
        agent=agent,
        launched=launched,
        budget=budget,
    )


def render_run_summary(run: MegalaunchRun) -> str:
    """Render a compact markdown summary for CLI output or blackboards."""
    counts = run.counts
    lines = [
        f"Run: {run.started_at.isoformat()}",
        "",
        "Counts:",
    ]
    for key in (
        "launched",
        "completed",
        "blocked",
        "skipped-human-gate",
        "skipped-unresolved-blocker",
        "skipped-budget",
        "failed",
    ):
        lines.append(f"- {key}: {counts[key]}")
    lines.extend(["", "Outcomes:"])
    if not run.results:
        lines.append("- none")
    for result in run.results:
        budget = ""
        if result.budget is not None and result.budget.detail != result.detail:
            budget = f" (budget: {result.budget.detail})"
        lines.append(f"- {result.slug}: {result.outcome} - {result.detail}{budget}")
    return "\n".join(lines) + "\n"


def trim_megalaunch_blackboard_text(text: str, summary: str) -> str:
    """Replace all old megalaunch run sections with the latest summary."""
    heading = "## Megalaunch Run Summary"
    lines = text.splitlines()
    kept: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == heading:
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            continue
        kept.append(lines[i])
        i += 1
    base = "\n".join(kept).rstrip()
    return f"{base}\n\n{heading}\n\n{summary.rstrip()}\n"


def write_run_summary(blackboard_path: Path, run: MegalaunchRun) -> None:
    """Write the latest run summary while trimming old megalaunch noise."""
    region = read_blackboard(blackboard_path)
    replace_blackboard(
        blackboard_path,
        trim_megalaunch_blackboard_text(region, render_run_summary(run)),
    )


__all__ = [
    "MegalaunchError",
    "MegalaunchResult",
    "MegalaunchRun",
    "render_run_summary",
    "run_megalaunch",
    "trim_megalaunch_blackboard_text",
    "write_run_summary",
]
