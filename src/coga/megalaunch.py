"""Sequential console launcher for launchable, agent-owned Coga work.

Only `active` tickets enter the default sweep. An `in_progress` ticket
belongs to a session some other process started — the sweep never grabs one;
resuming it must be deliberate. An **explicit selection** (the `--pick`
picker or `--relaunch`) is that deliberate act: selected tickets may be
`active` or `in_progress`, and a selected ticket
that turns out unlaunchable (wrong owner, draft/paused/done, script step) is
reported loudly instead of silently skipped — the human named it, so its
outcome is owed back. An optional directory narrows either mode to a `tasks/`
sub-tree, exactly like `coga status <dir>`.

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

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from coga import usage_probe
from coga.blackboard import open_blockers
from coga.commands.launch import (
    _interactive_stdio_has_tty,
    spawn_agent_session,
)
from coga.commands.launch_script import is_script_launch
from coga.recurring_runner import (
    _recurring_idle_timeout,
    _recurring_max_session,
)
from coga.compose import ComposeError, compose_prompt
from coga.config import Config, ConfigError, SecretError, build_launch_env, load_config
from coga.github_preflight import check_git_auth, check_git_remote
from coga.logfile import first_activity_map
from coga.mark import mark_in_progress
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import TaskRef, filter_tasks_under, list_tasks, read_ticket
from coga.ticket import Ticket, TicketError, TicketNotFoundError
from coga.validate import TaskValidationError


class MegalaunchError(Exception):
    """Megalaunch cannot run at all — e.g. no TTY for the interactive REPLs."""


MegalaunchOutcome = Literal[
    "completed",
    "blocked",
    "skipped-human-gate",
    "skipped-unresolved-blocker",
    "skipped-budget",
    "skipped-unlaunchable",
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
    agent_override: str | None = None
    directory: str | None = None
    selection: tuple[str, ...] | None = None
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
            "skipped-unlaunchable": 0,
            "failed": 0,
        }
        for result in self.results:
            counts[result.outcome] += 1
        return counts


def run_megalaunch(
    cfg: Config | None = None,
    *,
    max_tasks: int | None = None,
    agent_override: str | None = None,
    directory: str | None = None,
    selection: list[str] | None = None,
    max_steps_per_task: int = 8,
    probes: dict[str, usage_probe.UsageProbe] | None = None,
) -> MegalaunchRun:
    """Attempt launchable `active` tasks sequentially, each under the budget guard.

    `directory` narrows the sweep to that `tasks/` sub-tree (nested tasks
    included), same semantics as `coga status <dir>` — an unknown directory
    raises `UnknownDirectoryError` rather than sweeping nothing silently.

    `agent_override` launches swept tickets with that configured agent type
    instead of each ticket's `assignee:` — ephemeral, with the same semantics
    as `coga launch --agent`: the ticket is never rewritten, a human-assigned
    ticket is not converted into an agent step (still a human gate), and on a
    chained task the override applies only to the first launched step, so
    `other-agent` rotation on later steps still lands on the ticket's
    resolved assignee.

    `selection` (exact `id_slug`s) switches to explicit mode: only the named
    tasks run, `in_progress` ones are resumed (naming a task is the deliberate
    act the default sweep refuses to infer), and a named task that can't launch
    — wrong owner, draft/paused/done — is reported as
    `skipped-unlaunchable` instead of dropped. A selection slug matching no
    task raises `MegalaunchError`.
    """
    cfg = cfg or load_config()
    if agent_override is not None:
        cfg.agent_type(agent_override)
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

    # Validates the directory up front (fail loud on a typo) and narrows the
    # queue before any ticket is read, so out-of-scope work is never counted.
    queue = filter_tasks_under(_tasks_oldest_first(cfg), directory, cfg)
    explicit = selection is not None
    if explicit:
        wanted = set(selection or [])
        queue = [ref for ref in queue if ref.id_slug in wanted]
        missing = wanted - {ref.id_slug for ref in queue}
        if missing:
            listed = ", ".join(sorted(missing))
            raise MegalaunchError(f"Selected tasks not found: {listed}")

    for ref in queue:
        if max_tasks is not None and attempted >= max_tasks:
            break
        try:
            ticket = read_ticket(ref)
        except TicketNotFoundError:
            # The queue is a snapshot; a session launched earlier in this
            # sweep may legitimately reap a finished task (retire deletes the
            # source directory). A vanished ref is not a failure — skip it,
            # loudly only when the human explicitly named it.
            if explicit:
                results.append(
                    _result(ref, "skipped-unlaunchable", "task no longer exists")
                )
            continue
        except TicketError as exc:
            results.append(_result(ref, "failed", f"unreadable ticket: {exc}"))
            continue

        # Scope the sweep to the running operator's own work. On a shared repo a
        # daily sweep must not launch (and spend budget on) other people's
        # tickets, so a ticket owned by anyone but `cfg.current_user` is skipped
        # silently — like the status skip below, it never enters `results`, so
        # other owners' work doesn't inflate the summary counts. `ticket.owner`
        # is `None` when the field is absent, so owner-less tickets are excluded
        # too. Part 1 guarantees `current_user` is a real configured name, never
        # a guess, so this filter is trustworthy for unattended runs. An
        # explicitly selected ticket is never dropped silently — the human
        # named it, so its outcome is owed back (still not launched: someone
        # else's work is theirs to start).
        if ticket.owner != cfg.current_user:
            if explicit:
                results.append(
                    _result(
                        ref,
                        "skipped-unlaunchable",
                        f"owned by {ticket.owner or 'nobody'}, not "
                        f"{cfg.current_user}",
                        ticket.assignee,
                    )
                )
            continue

        # `active` (launchable) and `blocked` (reportable) tickets are in
        # scope. In the default sweep, draft/paused/done are ignored — never
        # launched and never counted as a result — and `in_progress` is
        # ignored too: that status means some other session owns the step
        # right now (or crashed mid-step), and neither is the sweep's to grab.
        # An explicit selection is the deliberate resume the sweep refuses to
        # infer: `in_progress` launches, everything else unlaunchable is
        # reported loudly.
        launchable = {"active", "in_progress", "blocked"} if explicit else {"active", "blocked"}
        if ticket.status not in launchable:
            if explicit:
                results.append(
                    _result(
                        ref,
                        "skipped-unlaunchable",
                        f"status is {ticket.status}",
                        ticket.assignee,
                    )
                )
            continue
        candidate = _candidate_result(
            cfg, ref, ticket, probes, agent_override=agent_override, explicit=explicit
        )
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
                agent_override=agent_override,
                max_steps_per_task=max_steps_per_task,
                idle_timeout=idle_timeout,
                max_session=max_session,
            )
        )

    return MegalaunchRun(
        started_at=started_at,
        agent_override=agent_override,
        directory=directory,
        selection=tuple(selection) if selection is not None else None,
        results=results,
    )


def launchable_candidates(
    cfg: Config,
    *,
    directory: str | None = None,
) -> list[tuple[TaskRef, Ticket]]:
    """The tasks the interactive picker offers, oldest-first.

    The operator's own `active` and `in_progress` tickets whose assignee is a
    configured agent and whose current step isn't script-backed — the set an
    explicit selection could actually launch. Unreadable tickets are skipped
    here (the picker offers choices; the run reports failures).
    """
    candidates: list[tuple[TaskRef, Ticket]] = []
    for ref in filter_tasks_under(_tasks_oldest_first(cfg), directory, cfg):
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.owner != cfg.current_user:
            continue
        if ticket.status not in {"active", "in_progress"}:
            continue
        if ticket.assignee not in cfg.agents:
            continue
        if ticket.current_step() is None or is_script_launch(cfg, ticket):
            continue
        candidates.append((ref, ticket))
    return candidates


def _selection_path(cfg: Config) -> Path:
    """Machine-local home of the last confirmed selection.

    Lives under the gitignored `.coga/` (vendored CLI, worktrees) because the
    selection is operator/machine state, not team state — committing it would
    make one person's `--relaunch` queue everyone's.
    """
    return cfg.repo_root / ".coga" / "megalaunch-selection.json"


def save_selection(cfg: Config, slugs: list[str]) -> None:
    """Persist a confirmed selection for a later `--relaunch`."""
    path = _selection_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "selected": list(slugs),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")


def load_selection(cfg: Config) -> list[str]:
    """Read the last confirmed selection; `MegalaunchError` when there is none."""
    path = _selection_path(cfg)
    if not path.is_file():
        raise MegalaunchError(
            "No saved selection to relaunch — confirm a picker run first "
            "(`coga megalaunch --pick`)."
        )
    try:
        payload = json.loads(path.read_text())
        slugs = payload["selected"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise MegalaunchError(f"Unreadable saved selection at {path}: {exc}") from exc
    if not isinstance(slugs, list) or not all(isinstance(s, str) for s in slugs):
        raise MegalaunchError(f"Unreadable saved selection at {path}: not a slug list")
    return slugs


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
    *,
    agent_override: str | None = None,
    explicit: bool = False,
) -> MegalaunchResult | None:
    blockers = open_blockers(ref.ticket_path)
    if ticket.status == "blocked":
        detail = "; ".join(blocker.reason for blocker in blockers) or "status is blocked"
        return _result(ref, "skipped-unresolved-blocker", detail, ticket.assignee)

    # An explicitly selected `in_progress` ticket goes through the same gates
    # as an `active` one — a resume must not dodge the script-step or budget
    # guard just because a prior session already flipped the status.
    launchable = {"active", "in_progress"} if explicit else {"active"}
    if ticket.status not in launchable:
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

    # The override agent is the one that will spend, so its window is the
    # one the guard reads. Human-gate checks above stay on `ticket.assignee`:
    # the override never converts a human handoff into an agent step.
    launch_assignee = agent_override or ticket.assignee
    budget = usage_probe.check_budget(probes, launch_assignee, cfg.megalaunch)
    if not budget.allowed:
        return _result(
            ref,
            "skipped-budget",
            budget.detail,
            launch_assignee,
            budget=budget,
        )
    return None


def _launch_until_stop(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    probes: dict[str, usage_probe.UsageProbe],
    *,
    agent_override: str | None,
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
        # The override applies only to the task's first launched step — the
        # same rule as `coga launch --agent` — so `other-agent` rotation on
        # later steps still lands on the ticket's resolved assignee.
        launch_assignee = (
            ticket.assignee if launched else (agent_override or ticket.assignee)
        )

        # Re-probe before every launch — the previous step just spent budget,
        # and the agent's own usage window is the only accounting we trust.
        budget = usage_probe.check_budget(probes, launch_assignee, cfg.megalaunch)
        last_budget = budget
        if not budget.allowed:
            return _result(
                ref,
                "skipped-budget",
                budget.detail,
                launch_assignee,
                launched=launched,
                budget=budget,
            )

        preflight = _preflight_agent_launch(cfg, ref, ticket, launch_assignee)
        if preflight is not None:
            return _result(
                ref,
                "failed",
                preflight,
                launch_assignee,
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
            agent = cfg.agent_type(launch_assignee or "")
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
                env=env,
                actor="megalaunch",
                log_message="launched via coga megalaunch",
                name=before.title or "",
                idle_timeout=idle_timeout,
                max_session=max_session,
                label="Megalaunch",
                warn_blackboard=True,
                capture_usage=True,
            )
        except (ComposeError, ConfigError, SecretError) as exc:
            return _result(ref, "failed", str(exc), launch_assignee, budget=budget)
        except FileNotFoundError:
            return _result(
                ref,
                "failed",
                f"agent CLI {agent.cli!r} not found",
                launch_assignee,
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


def _preflight_agent_launch(
    cfg: Config, ref: TaskRef, ticket: Ticket, launch_assignee: str | None
) -> str | None:
    try:
        agent = cfg.agent_type(launch_assignee or "")
    except ConfigError as exc:
        return str(exc)
    if ticket.status not in {"active", "in_progress"}:
        return f"status is {ticket.status}; expected active or in_progress"
    if shutil.which(agent.cli) is None:
        return f"agent CLI {agent.cli!r} not found in PATH"
    try:
        compose_prompt(cfg, ref, ticket)
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
    ]
    if run.agent_override is not None:
        lines.extend(["", f"Agent override: {run.agent_override}"])
    if run.directory is not None:
        lines.extend(["", f"Directory: {run.directory}"])
    if run.selection is not None:
        lines.extend(["", f"Selection: {', '.join(run.selection)}"])
    lines.extend(["", "Counts:"])
    for key in (
        "launched",
        "completed",
        "blocked",
        "skipped-human-gate",
        "skipped-unresolved-blocker",
        "skipped-budget",
        "skipped-unlaunchable",
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
    "launchable_candidates",
    "load_selection",
    "render_run_summary",
    "run_megalaunch",
    "save_selection",
    "trim_megalaunch_blackboard_text",
    "write_run_summary",
]
