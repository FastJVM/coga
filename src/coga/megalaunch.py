"""Sequential console launcher for launchable, agent-owned Coga work.

The default sweep covers the operator's `active` and `in_progress` tickets:
`active` work starts, `in_progress` work — a session another process started
that has since crashed or been torn down mid-step — resumes, exactly like a
manual `coga launch <slug>`. An **explicit selection** (the `--pick` picker
or `--relaunch`) runs only the named tasks, any owner's, and reaches wider —
any status but `done` — by staging the run in three phases so every
human-in-the-loop step lands before the first launch: **prepare** (when the
operator accepts the CLI's batch prompt, each picked `draft` runs the guided
`coga ticket` authoring interview so a not-ready ticket becomes launchable),
**activate** (every draft/paused/blocked → `active`), then **launch** (each
activated ticket runs). A picked `blocked`
ticket resumes interactively with the resolve-or-re-block preamble, returning
to `blocked` if the session exits with the ask still open. A selected ticket
that still can't launch (done, or a draft the interview left with no workflow)
is reported loudly instead of silently skipped — the human named it, so its
outcome is owed back. An optional directory narrows either mode to a `tasks/`
sub-tree, exactly like `coga status <dir>`.

Megalaunch is a set of normal interactive launches, not a headless drain: each
eligible step spawns the agent REPL under the PTY watcher exactly like
`coga launch`, so output streams live to the console and the done-sentinel
(`coga bump` / `mark done` / `block`) tears the REPL down and hands control
back to the sweep. Recurring's idle-timeout / max-session backstops are armed
so one wedged agent can't starve the rest of the queue. Because the spawned
REPLs are interactive, the whole run requires a TTY — fail loud otherwise.
The TTY is transport, not an approval gate: a package-backed megalaunch prompt
directive tells the agent to announce its plan and continue, or to use
`coga block` when a real human decision or capability is unavailable.

Script launches run too: a ticket whose current step is script-backed or that
carries its own `script:` runs through the same `run_script_mode` path the
`coga launch` supervisor uses — no agent, no REPL.
Exit 0 advances the step and the chain continues; a non-zero exit leaves the
step put and fails that task's result without stopping the rest of the sweep.

Tasks are serviced oldest-first (first `coga/log.md` line per ref — committed
content, so the order survives clones where file mtimes don't).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Literal

from coga.blackboard import open_blockers
from coga.commands.launch import (
    _interactive_stdio_has_tty,
    spawn_agent_session,
)
from coga.commands.launch_script import (
    current_step_is_script,
    is_script_launch,
    run_script_mode,
)
from coga.recurring_runner import (
    _recurring_idle_timeout,
    _recurring_max_session,
)
from coga.compose import ComposeError, compose_prompt
from coga.config import Config, ConfigError, SecretError, build_launch_env, load_config
from coga.dependencies import agent_cli_missing_message
from coga.github_preflight import check_git_auth, check_git_remote
from coga.logfile import first_activity_map
from coga.mark import (
    BlackboardNeedsSynthesis,
    RequiredExtensionMissing,
    WorkflowMissing,
    mark_active,
    mark_blocked,
    mark_in_progress,
)
from coga.workflow import WorkflowError
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import (
    TaskNotFoundError,
    TaskRef,
    filter_tasks_under,
    list_tasks,
    read_ticket,
    resolve_bootstrap,
)
from coga.ticket import Ticket, TicketError, TicketNotFoundError
from coga.validate import TaskValidationError


class MegalaunchError(Exception):
    """Megalaunch cannot run at all — e.g. no TTY for the interactive REPLs."""


MegalaunchOutcome = Literal[
    "completed",
    "blocked",
    "skipped-human-gate",
    "skipped-unresolved-blocker",
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
    author_drafts: bool = False,
    max_steps_per_task: int = 8,
) -> MegalaunchRun:
    """Attempt launchable `active` and `in_progress` tasks sequentially.

    `directory` narrows the sweep to that `tasks/` sub-tree (nested tasks
    included), same semantics as `coga status <dir>` — an unknown directory
    raises `UnknownDirectoryError` rather than sweeping nothing silently.

    `agent_override` launches swept tickets with that configured agent type
    instead of each ticket's `assignee:` — ephemeral, with the same semantics
    as `coga launch --agent`: the ticket is never rewritten, a human-assigned
    ticket is not converted into an agent step (still a human gate), and on a
    chained task the override applies only to the first launched *agent* step
    (script steps run as scripts and never consume it), so `other-agent`
    rotation on later steps still lands on the ticket's resolved assignee.

    `selection` (exact `id_slug`s) switches to explicit mode: only the named
    tasks run, any owner's, and the run is staged so every human-in-the-loop
    step happens before the first launch — **prepare** (when `author_drafts`,
    each picked `draft` runs the guided `coga ticket` authoring interview so a
    not-ready ticket becomes launchable; the human can end the interview at
    once if it is already fine), then **activate** (every draft/paused/blocked
    → `active`), then **launch** (each activated ticket runs). A picked
    `blocked` ticket resumes interactively (re-blocked if the session exits
    with the ask still open); a named task that still can't launch — done, or
    a draft with no workflow to activate — is reported as
    `skipped-unlaunchable` instead of dropped. A selection slug matching no
    task raises `MegalaunchError`.

    `author_drafts` gates the prepare phase: the CLI sets it from a one-shot
    batch prompt when the confirmed selection contains drafts, so authoring is
    an opt-in the operator agreed to, never forced on every pick.
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
    # Liveness backstops for the spawned REPLs, resolved once per sweep with
    # the same precedence recurring uses (env override > [launch] config >
    # default). Human keystrokes count as activity, so an attended session
    # is only torn down when it is genuinely idle.
    idle_timeout = _recurring_idle_timeout(cfg)
    max_session = _recurring_max_session(cfg)

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
        results = _run_selection(
            cfg,
            queue,
            agent_override=agent_override,
            author_drafts=author_drafts,
            max_tasks=max_tasks,
            max_steps_per_task=max_steps_per_task,
            idle_timeout=idle_timeout,
            max_session=max_session,
        )
    else:
        results = _run_sweep(
            cfg,
            queue,
            agent_override=agent_override,
            max_tasks=max_tasks,
            max_steps_per_task=max_steps_per_task,
            idle_timeout=idle_timeout,
            max_session=max_session,
        )

    return MegalaunchRun(
        started_at=started_at,
        agent_override=agent_override,
        directory=directory,
        selection=tuple(selection) if selection is not None else None,
        results=results,
    )


def _run_sweep(
    cfg: Config,
    queue: list[TaskRef],
    *,
    agent_override: str | None,
    max_tasks: int | None,
    max_steps_per_task: int,
    idle_timeout: float | None,
    max_session: float | None,
) -> list[MegalaunchResult]:
    """The unattended sweep: the operator's own ready `active` / `in_progress`
    work, one launchable step at a time. Draft/paused/done are ignored and
    blocked is reported, never launched — resuming those needs a human, which
    only the explicit picker path provides.
    """
    results: list[MegalaunchResult] = []
    attempted = 0
    for ref in queue:
        if max_tasks is not None and attempted >= max_tasks:
            break
        try:
            ticket = read_ticket(ref)
        except TicketNotFoundError:
            # The queue is a snapshot; a session launched earlier in this
            # sweep may legitimately reap a finished task (retire deletes the
            # source directory). A vanished ref is not a failure — skip it
            # (the sweep never named it, so nothing is owed back).
            continue
        except TicketError as exc:
            results.append(_result(ref, "failed", f"unreadable ticket: {exc}"))
            continue

        # Scope the sweep to the running operator's own work. On a shared repo
        # a daily sweep must not launch other people's tickets, so a ticket
        # owned by anyone but `cfg.current_user` is skipped silently — it never
        # enters `results`, so other owners' work doesn't inflate the summary
        # counts. `ticket.owner` is `None` when the field is absent, so
        # owner-less tickets are excluded too. Part 1 guarantees `current_user`
        # is a real configured name, never a guess, so this filter is
        # trustworthy for unattended runs.
        if ticket.owner != cfg.current_user:
            continue
        if ticket.status not in {"active", "in_progress", "blocked"}:
            continue
        candidate = _candidate_result(cfg, ref, ticket, explicit=False)
        if candidate is not None:
            results.append(candidate)
            continue

        attempted += 1
        results.append(
            _launch_until_stop(
                cfg,
                ref,
                ticket,
                agent_override=agent_override,
                max_steps_per_task=max_steps_per_task,
                idle_timeout=idle_timeout,
                max_session=max_session,
            )
        )
    return results


def _run_selection(
    cfg: Config,
    queue: list[TaskRef],
    *,
    agent_override: str | None,
    author_drafts: bool,
    max_tasks: int | None,
    max_steps_per_task: int,
    idle_timeout: float | None,
    max_session: float | None,
) -> list[MegalaunchResult]:
    """The explicit picker path, staged so all human-in-the-loop prep lands
    before the first launch: **prepare** (author picked drafts, when the
    operator opted in), then **activate** (draft/paused/blocked → active),
    then **launch** (run each).

    Batching the phases means the operator answers every authoring interview
    and every activation up front, then the working launches proceed without
    further gating them on a not-yet-ready ticket further down the list.
    """
    results: list[MegalaunchResult] = []

    # Phase 1 — Prepare. When the operator opted in (the CLI's one-shot batch
    # prompt, asked only when the pick contains drafts), run the guided
    # `coga ticket` authoring interview on each picked draft, bringing a
    # not-ready ticket to a launchable shape (workflow, contexts, assignee).
    # The human ends the interview immediately if the draft is already fine —
    # authoring leaves the status at `draft`, and an unreadable/vanished ref is
    # left for phase 2 to report.
    if author_drafts:
        for ref in queue:
            try:
                ticket = read_ticket(ref)
            except TicketError:
                continue
            if ticket.status == "draft":
                _author_draft(cfg, ref, ticket)

    # Phase 2 — Activate. Bring every picked draft/paused/blocked to `active`
    # (a blocked ticket keeps its open asks for the launch-time preamble), and
    # report the ones that still can't launch. What survives is the launch
    # plan, each entry remembering whether it was a blocked resume.
    launch_plan: list[tuple[TaskRef, bool]] = []
    for ref in queue:
        try:
            ticket = read_ticket(ref)
        except TicketNotFoundError:
            results.append(
                _result(ref, "skipped-unlaunchable", "task no longer exists")
            )
            continue
        except TicketError as exc:
            results.append(_result(ref, "failed", f"unreadable ticket: {exc}"))
            continue
        if ticket.status == "done":
            results.append(
                _result(ref, "skipped-unlaunchable", "status is done", ticket.assignee)
            )
            continue
        candidate = _candidate_result(cfg, ref, ticket, explicit=True)
        if candidate is not None:
            results.append(candidate)
            continue
        was_blocked = ticket.status == "blocked"
        if ticket.status in {"draft", "paused", "blocked"}:
            failure = _activate_for_launch(cfg, ref, ticket)
            if failure is not None:
                results.append(failure)
                continue
            # Activation froze the workflow and seeded step 1; a non-script
            # ticket with no resulting step can't be agent-launched.
            if not is_script_launch(cfg, ticket) and ticket.current_step() is None:
                results.append(
                    _result(
                        ref,
                        "skipped-human-gate",
                        "no current workflow step",
                        ticket.assignee,
                    )
                )
                continue
        launch_plan.append((ref, was_blocked))

    # Phase 3 — Launch. Every entry is now an activated ticket; run them one at
    # a time, honouring `--max-tasks` over the launches.
    attempted = 0
    for ref, blocked_resume in launch_plan:
        if max_tasks is not None and attempted >= max_tasks:
            break
        try:
            ticket = read_ticket(ref)
        except TicketNotFoundError:
            results.append(
                _result(ref, "skipped-unlaunchable", "task no longer exists")
            )
            continue
        except TicketError as exc:
            results.append(_result(ref, "failed", f"unreadable ticket: {exc}"))
            continue
        attempted += 1
        results.append(
            _launch_until_stop(
                cfg,
                ref,
                ticket,
                agent_override=agent_override,
                max_steps_per_task=max_steps_per_task,
                idle_timeout=idle_timeout,
                max_session=max_session,
                blocked_resume=blocked_resume,
            )
        )
    return results


def _author_draft(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Run the guided `coga ticket` authoring interview on a picked draft.

    Best-effort prep, not a launch: it reuses the same authoring session
    `coga ticket <slug>` runs, so the draft can be edited into a launchable
    shape before phase 2 tries to activate it. All of the authoring path's
    hard failures `sys.exit` (no TTY, missing CLI, compose/finalize error) —
    catch that here so a draft that can't be authored simply stays a draft
    (phase 2 then reports it not-ready) instead of killing the whole run.
    """
    from coga.commands.ticket import (
        AUTHORING_KICKOFF_EDIT,
        _authoring_ticket,
        _run_authoring_session,
    )

    try:
        bootstrap_ref = resolve_bootstrap(cfg, "ticket")
    except TaskNotFoundError:
        return
    bootstrap_ticket = read_ticket(bootstrap_ref)
    launch_assignee = (
        bootstrap_ticket.assignee or ticket.agent or ticket.assignee
    )
    if not launch_assignee:
        return
    try:
        _run_authoring_session(
            cfg=cfg,
            ref=ref,
            ticket=_authoring_ticket(ticket),
            launch_assignee=launch_assignee,
            kickoff=AUTHORING_KICKOFF_EDIT,
            bootstrap_title=bootstrap_ticket.title or "",
        )
    except SystemExit:
        # `_run_authoring_session` exits on its own errors; swallow it so the
        # rest of the selection still runs. The draft is untouched or
        # partially authored — phase 2 decides launchability from its state.
        return


def launchable_candidates(
    cfg: Config,
    *,
    directory: str | None = None,
) -> list[tuple[TaskRef, Ticket]]:
    """The tasks the interactive picker offers, oldest-first.

    Everything an explicit pick could actually launch — any owner, any status
    but `done`: `active`/`in_progress` start or resume, `blocked` resumes
    interactively when it has open asks, and any `draft` is offered
    unconditionally — the picker runs the guided authoring interview on a
    picked draft first, so a not-yet-ready draft (no workflow or agent
    assignee) is exactly what that phase exists to fix. Non-draft tasks must
    be launchable as they stand: a script launch (script-backed step or a
    ticket-owned `script:`) regardless of assignee, otherwise agent-assigned
    with a real current step. Unreadable tickets are skipped here (the picker
    offers choices; the run reports failures).
    """
    candidates: list[tuple[TaskRef, Ticket]] = []
    for ref in filter_tasks_under(_tasks_oldest_first(cfg), directory, cfg):
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.status == "done":
            continue
        if ticket.status == "draft":
            # Offered as-is: the prepare phase authors it into shape.
            candidates.append((ref, ticket))
            continue
        if not is_script_launch(cfg, ticket):
            if ticket.assignee not in cfg.agents or ticket.current_step() is None:
                continue
        if ticket.status == "blocked" and not open_blockers(ref.ticket_path):
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
    *,
    explicit: bool = False,
) -> MegalaunchResult | None:
    blockers = open_blockers(ref.ticket_path)
    if ticket.status == "blocked":
        # The unattended sweep never resumes a blocked ticket — that needs a
        # human in the loop. An explicit pick *is* that human act: the launch
        # activates it and the composed prompt gains the resolve-or-re-block
        # preamble, so only an ask-less blocked ticket (nothing to resolve)
        # stays unlaunchable.
        if explicit:
            if not blockers:
                return _result(
                    ref,
                    "skipped-unlaunchable",
                    "blocked but has no open blocker asks to resolve",
                    ticket.assignee,
                )
        else:
            detail = (
                "; ".join(blocker.reason for blocker in blockers)
                or "status is blocked"
            )
            return _result(ref, "skipped-unresolved-blocker", detail, ticket.assignee)
    elif blockers and ticket.status in {"active", "in_progress"} and not explicit:
        # An `in_progress` resume goes through the same gates as an `active`
        # start — it must not dodge the blocker gate just because a prior
        # session already flipped the status.
        detail = "; ".join(blocker.reason for blocker in blockers)
        return _result(ref, "skipped-unresolved-blocker", detail, ticket.assignee)

    # A script launch — a script-backed current step or a
    # ticket-owned `script:` — is launchable regardless of assignee: the sweep
    # runs the script itself, exactly like the `coga launch` supervisor. This
    # mirrors the script exemption in launch's `_refuse_human_handoff_launch`.
    if is_script_launch(cfg, ticket):
        return None

    if ticket.assignee not in cfg.agents:
        return _result(
            ref,
            "skipped-human-gate",
            f"assignee {ticket.assignee or 'unassigned'} is not a configured agent",
            ticket.assignee,
        )

    # A draft has no current step yet — activation freezes the workflow and
    # seeds step 1, so its step/script gates run post-activation in
    # `_launch_until_stop`. Everything else is gated here.
    if ticket.status == "draft":
        return None
    if ticket.current_step() is None:
        return _result(ref, "skipped-human-gate", "no current workflow step", ticket.assignee)
    return None


def _launch_until_stop(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    agent_override: str | None,
    max_steps_per_task: int,
    idle_timeout: float | None = None,
    max_session: float | None = None,
    blocked_resume: bool = False,
) -> MegalaunchResult:
    # `ticket` is already `active` / `in_progress` — the sweep only reaches
    # here for ready work, and the selection path activates draft/paused/
    # blocked in its own phase before launching. `blocked_resume` marks a
    # ticket that was blocked when picked: the composed prompt carries the
    # resolve-or-re-block preamble off the blackboard's still-open asks, and an
    # exit that leaves an ask open returns it to `blocked` below.
    launched = False
    first_agent_step = True
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
            )

        # A script launch — the current step's single skill declares a
        # `script:`, or the ticket carries its own
        # `script:` — runs in-process through the same `run_script_mode` path
        # the `coga launch` supervisor uses: exit 0 advances the step (or
        # finishes the task), non-zero leaves the step put. No agent, no REPL,
        # and no assignee gate — scripts run regardless of who is assigned,
        # exactly like `coga launch`.
        if is_script_launch(cfg, ticket):
            launched = True
            failure = _run_script_step(cfg, ref, ticket)
            if failure is not None:
                return _result(ref, "failed", failure, ticket.assignee, launched=True)
            if not ref.ticket_path.exists():
                # A script may legitimately delete its own task (e.g. the
                # bootstrap/delete-task skill) — a clean terminal state.
                return _result(
                    ref,
                    "completed",
                    "task removed by script step",
                    ticket.assignee,
                    launched=True,
                )
            after = read_ticket(ref)
            stop = _chain_stop_result(cfg, ref, after)
            if stop is not None:
                return stop
            ticket = after
            continue

        if ticket.assignee not in cfg.agents:
            return _result(
                ref,
                "completed",
                f"handed off to {ticket.assignee or 'unassigned'}",
                ticket.assignee,
                launched=launched,
            )
        # The override applies only to the task's first launched *agent* step
        # — the same rule as `coga launch --agent`, where a script step never
        # consumes it — so `other-agent` rotation on later steps still lands
        # on the ticket's resolved assignee.
        launch_assignee = (
            (agent_override or ticket.assignee) if first_agent_step else ticket.assignee
        )
        first_agent_step = False

        preflight = _preflight_agent_launch(cfg, ref, ticket, launch_assignee)
        if preflight is not None:
            return _result(
                ref,
                "failed",
                preflight,
                launch_assignee,
                launched=launched,
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
                return _result(ref, "failed", str(exc), ticket.assignee)

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
                prompt_suffix=_megalaunch_prompt_suffix(),
                label="Megalaunch",
                warn_blackboard=True,
            )
        except (ComposeError, ConfigError, SecretError) as exc:
            return _result(ref, "failed", str(exc), launch_assignee)
        except FileNotFoundError:
            return _result(
                ref,
                "failed",
                f"agent CLI {agent.cli!r} not found",
                launch_assignee,
            )

        launched = True
        after = read_ticket(ref)
        if blocked_resume:
            # A resumed blocked launch may run to `in_progress` so the session
            # can discuss, `coga unblock`, and continue. If it exited with the
            # ask still open, return it to the blocked queue (visible to
            # `status --blocked` and blocker reminders) instead of chaining.
            blocked_resume = False
            reblocked = _reblock_unresolved(cfg, ref, after)
            if reblocked is not None:
                return reblocked
        if after.status == "blocked":
            blockers = open_blockers(ref.ticket_path)
            detail = "; ".join(blocker.reason for blocker in blockers) or "blocked"
            return _result(ref, "blocked", detail, after.assignee, launched=True)
        if session.termination_kind == "timeout":
            timeout_reason = getattr(session, "termination_reason", None)
            detail = (
                f"agent hit {timeout_reason} without signalling done"
                if timeout_reason
                else "agent hit a liveness limit without signalling done"
            )
            return _result(
                ref,
                "failed",
                detail,
                after.assignee,
                launched=True,
            )
        if session.exit_code != 0:
            return _result(
                ref,
                "failed",
                f"agent exited with code {session.exit_code}",
                after.assignee,
                launched=True,
            )
        stop = _chain_stop_result(cfg, ref, after)
        if stop is not None:
            return stop
        if (after.step, after.status) == (before.step, before.status):
            return _result(
                ref,
                "failed",
                "agent exited without changing task state",
                after.assignee,
                launched=True,
            )
        ticket = after


def _activate_for_launch(
    cfg: Config, ref: TaskRef, ticket: Ticket
) -> MegalaunchResult | None:
    """Bring an explicitly picked draft / paused / blocked ticket to `active`.

    Mirrors `coga launch`'s inline auto-activation, but returns a loud result
    instead of exiting the process — one bad pick must not kill the sweep.
    `mark_active` mutates `ticket` in place (status, frozen workflow, seeded
    step), so the caller's launch loop continues off the same object.
    """
    prior = ticket.status
    try:
        mark_active(
            cfg,
            ref,
            ticket,
            actor="megalaunch",
            log_message=f"activated ({prior} → active) — explicit megalaunch pick",
            echo=None,
        )
    except WorkflowMissing:
        return _result(
            ref,
            "skipped-unlaunchable",
            f"{prior} with no workflow — set `workflow:` in ticket.md or run "
            f"`coga ticket {ref.id_slug}`",
            ticket.assignee,
        )
    except WorkflowError as exc:
        return _result(
            ref,
            "skipped-unlaunchable",
            f"`workflow:` ref could not be frozen — {exc}",
            ticket.assignee,
        )
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        return _result(
            ref,
            "skipped-unlaunchable",
            f"required extension field(s) empty: {names}",
            ticket.assignee,
        )
    except BlackboardNeedsSynthesis as exc:
        return _result(
            ref,
            "skipped-unlaunchable",
            f"blackboard needs synthesis before first launch: {exc.reason}",
            ticket.assignee,
        )
    except TaskValidationError as exc:
        return _result(ref, "failed", str(exc), ticket.assignee)
    return None


def _reblock_unresolved(
    cfg: Config, ref: TaskRef, after: Ticket
) -> MegalaunchResult | None:
    """Return an unresolved blocked-ticket resume to the blocked queue.

    Same contract as `coga launch`'s `_reblock_unresolved_resume`: the resumed
    session was allowed to reach `in_progress`, but exiting with the ask still
    open must keep it visible to `status --blocked` and blocker reminders.
    """
    if not ref.ticket_path.exists() or after.status != "in_progress":
        return None
    blockers = open_blockers(ref.ticket_path)
    if not blockers:
        return None
    owner = after.owner or cfg.current_user
    detail = "; ".join(b.reason for b in blockers)
    try:
        mark_blocked(
            cfg,
            ref,
            after,
            actor="system",
            log_message=(
                "blocked: unresolved blocker still open after resumed "
                "megalaunch pick exited"
            ),
            slack_text=(
                f"🛑 {cfg.current_user} still blocked "
                f"*{ref.id_slug}* \"{after.title}\": {detail}"
            ),
            echo=(
                f"{ref.id_slug}: blocked (unresolved blocker still open; "
                f"owner {owner} needs to answer)"
            ),
        )
    except TaskValidationError as exc:
        return _result(ref, "failed", str(exc), after.assignee, launched=True)
    return _result(ref, "blocked", detail, after.assignee, launched=True)


def _run_script_step(cfg: Config, ref: TaskRef, ticket: Ticket) -> str | None:
    """Run the task's script in-process; returns the failure detail, or None.

    The same `run_script_mode` path the `coga launch` supervisor uses: it
    marks an `active` ticket in_progress, runs the script, and on exit 0
    advances the step (or finishes the task after the final one). All its
    failure paths `sys.exit` — catch that here so one failed script fails this
    task's result instead of killing the rest of the sweep.
    """
    step = ticket.current_step()
    where = (
        f"script step {ticket.step_index()} ({step['name']})"
        if step is not None and current_step_is_script(cfg, ticket)
        else "ticket script"
    )
    try:
        run_script_mode(cfg, ref, ticket)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        return f"{where} exited with code {code}"
    return None


def _chain_stop_result(
    cfg: Config, ref: TaskRef, after: Ticket
) -> MegalaunchResult | None:
    """Terminal chain state after a step ran, or None to keep chaining.

    Shared by the agent and script branches of `_launch_until_stop`; every
    result it returns is launched work.
    """
    if after.status == "blocked":
        blockers = open_blockers(ref.ticket_path)
        detail = "; ".join(blocker.reason for blocker in blockers) or "blocked"
        return _result(ref, "blocked", detail, after.assignee, launched=True)
    if after.status == "done":
        return _result(ref, "completed", "task done", after.assignee, launched=True)
    if after.status != "in_progress":
        return _result(
            ref,
            "completed",
            f"status is {after.status}",
            after.assignee,
            launched=True,
        )
    if after.assignee not in cfg.agents:
        return _result(
            ref,
            "completed",
            f"handed off to {after.assignee or 'unassigned'}",
            after.assignee,
            launched=True,
        )
    return None


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
        return agent_cli_missing_message(agent.cli)
    try:
        compose_prompt(cfg, ref, ticket)
        _megalaunch_prompt_suffix()
        build_launch_env(cfg, ticket.secrets)
    except (ConfigError, ComposeError, SecretError) as exc:
        return str(exc)
    if cfg.git_enabled and check_git_remote(cfg.git_remote).ok:
        auth = check_git_auth(cfg.git_remote)
        if not auth.ok:
            return f"git push access unavailable: {auth.detail}"
    return None


def _megalaunch_prompt_suffix() -> str:
    """Return package-backed execution guidance unique to the queue runner."""
    try:
        prompt = files("coga.resources").joinpath("prompt-megalaunch.md").read_text()
    except OSError as exc:
        raise ComposeError(
            "Megalaunch execution prompt is missing from the installed Coga "
            "package: prompt-megalaunch.md"
        ) from exc
    return f"\n\n{prompt.strip()}\n"


def _result(
    ref: TaskRef,
    outcome: MegalaunchOutcome,
    detail: str,
    agent: str | None = None,
    *,
    launched: bool = False,
) -> MegalaunchResult:
    return MegalaunchResult(
        slug=ref.id_slug,
        outcome=outcome,
        detail=detail,
        agent=agent,
        launched=launched,
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
        "skipped-unlaunchable",
        "failed",
    ):
        lines.append(f"- {key}: {counts[key]}")
    lines.extend(["", "Outcomes:"])
    if not run.results:
        lines.append("- none")
    for result in run.results:
        lines.append(f"- {result.slug}: {result.outcome} - {result.detail}")
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
