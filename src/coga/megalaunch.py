"""Sequential console launcher for launchable, agent-owned Coga work.

The default sweep covers the operator's `active` and `in_progress` tickets:
`active` work starts, `in_progress` work — a session another process started
that has since crashed or been torn down mid-step — resumes, exactly like a
manual `coga launch <slug>`. After that pass, a fixed-point dependency drain
re-lists the operator's blocked tickets: when an open blocker names a known
task that is now done (or was deleted after finishing), megalaunch resolves
the ask with an explicit automatic answer and relaunches the dependent. Each
drain launch restarts the walk; a full pass with no launch ends the run.

An **explicit selection** (the `--pick` picker or `--relaunch`) runs only the
named tasks, any owner's, and reaches wider —
any non-terminal status — by staging the run in three phases so every
human-in-the-loop step lands before the first launch: **prepare** (when the
operator accepts the CLI's batch prompt, each picked `draft` runs the guided
`coga ticket` authoring interview so a not-ready ticket becomes launchable),
**check** (every draft/paused/blocked is validated against the `active` view it
would get, and the ones that still can't launch are reported), then **launch**
(each remaining ticket is activated and run, in that order, as its own turn
comes). A picked `blocked`
ticket resumes interactively with the resolve-or-re-block preamble, returning
to `blocked` if the session exits with the ask still open. A selected ticket
that still can't launch (terminal, or a draft the interview left with no workflow)
is reported loudly instead of silently skipped — the human named it, so its
outcome is owed back. An optional directory narrows either mode to a `tasks/`
sub-tree, exactly like `coga status <dir>`.

Megalaunch is a set of normal interactive launches, not a headless drain: each
eligible step spawns the agent REPL under the PTY watcher exactly like
`coga launch`, so output streams live to the console and the done-sentinel
(`coga bump` / `mark done` / `mark canceled` / `block`) tears the REPL down
and hands control back to the sweep. Recurring's idle-timeout / max-session backstops are armed
so one wedged agent can't starve the rest of the queue. Because the spawned
REPLs are interactive, the whole run requires a TTY — fail loud otherwise.
The TTY is transport, not an approval gate: a package-backed megalaunch prompt
directive tells the agent to announce its plan and continue, or to use
`coga block` when a real human decision or capability is unavailable.

Tasks are serviced oldest-first (first `coga/log.md` line per ref — committed
content, so the order survives clones where file mtimes don't), except that a
sub-directory holding `1-`/`2-`/`3-` prefixed tasks runs as one contiguous
block in number order, anchored where its oldest task would have run. See
`coga.service_order` for the key. The `--pick` list *displays* like the
default `coga status` view instead (last updated, newest first), but the
confirmed set still launches in this drain order.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from coga import git
from coga.blackboard import (
    Blocker,
    open_blockers,
    parse_blockers_text,
    resolve_open_blockers,
    update_blackboard_under_barrier,
)
from coga.commands.launch import (
    _interactive_stdio_has_tty,
    missing_launch_file_message,
    spawn_agent_session,
)
from coga.recurring_runner import (
    _recurring_idle_timeout,
    _recurring_max_session,
)
from coga.compose import ComposeError, compose_prompt
from coga.config import (
    AgentType,
    Config,
    ConfigError,
    SecretError,
    build_launch_env,
    load_config,
)
from coga.dependencies import agent_cli_missing_message
from coga.github_preflight import check_git_auth, check_git_remote
from coga.logfile import first_activity_map
from coga.lifecycle import TERMINAL_STATUSES
from coga.mark import (
    BlackboardNeedsSynthesis,
    RequiredExtensionMissing,
    WorkflowMissing,
    mark_active,
    mark_blocked,
    mark_in_progress,
    prepare_active,
)
from coga.paths import log_path
from coga.repl_supervisor import build_supervised_step_env
from coga.workflow import WorkflowError
from coga.taskfile import (
    TaskFileError,
    read_blackboard,
    split_body,
)
from coga.service_order import service_order
from coga.tasks import (
    TaskNotFoundError,
    TaskRef,
    filter_tasks_under,
    is_under,
    list_tasks,
    read_ticket,
    resolve_bootstrap,
)
from coga.ticket import (
    PENDING_LAUNCH_GENERATION_PREFIX,
    Ticket,
    TicketError,
    TicketNotFoundError,
    admitted_launch_generation,
    pending_launch_generation,
    released_generation_from_pending,
    released_launch_generation,
)
from coga.validate import TaskValidationError
from coga.views import last_updated_map


class MegalaunchError(Exception):
    """Megalaunch cannot run at all — e.g. no TTY for the interactive REPLs."""


class _LaunchClaimRefused(Exception):
    """The published megalaunch claim stopped matching before PTY spawn."""


MegalaunchOutcome = Literal[
    "completed",
    "canceled",
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
    drained: bool = False


@dataclass(frozen=True)
class _PreparedAgentLaunch:
    """Fallible launch inputs materialized before lifecycle writes."""

    ticket: Ticket
    source_ticket_bytes: bytes
    agent: AgentType
    env: dict[str, str]
    prompt: str


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
            "drained": sum(1 for result in self.results if result.drained),
            "completed": 0,
            "canceled": 0,
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

    `agent_override` runs picked-draft authoring interviews and launches swept
    agent-owned tickets with that configured agent type instead of the default
    authoring agent / each ticket's `assignee:`. It is ephemeral and applies
    only to authoring plus the first launched step, so `other-agent` rotation
    on later steps still lands on the ticket's resolved assignee. Unlike an
    explicit `coga launch --agent`, megalaunch keeps its independent human
    gate: human-assigned working steps still skip.

    `selection` (exact `id_slug`s) switches to explicit mode: only the named
    tasks run, any owner's, and the run is staged so every human-in-the-loop
    step happens before the first launch — **prepare** (when `author_drafts`,
    each picked `draft` runs the guided `coga ticket` authoring interview so a
    not-ready ticket becomes launchable; the human can end the interview at
    once if it is already fine), then **check** (validate the prospective
    `active` view without writing it), then **launch** (re-read each pick,
    preflight its current prospective view, and activate it only as its own
    launch starts). A picked `blocked` ticket resumes interactively (re-blocked
    if the session exits with the ask still open); a named task that still
    can't launch — done, or a draft with no workflow to activate — is reported
    as `skipped-unlaunchable` instead of dropped. A selection slug matching no
    task raises `MegalaunchError`.

    `author_drafts` gates the prepare phase: the CLI sets it from a one-shot
    batch prompt when the confirmed selection contains drafts, so authoring is
    an opt-in the operator agreed to, never forced on every pick.

    The dependency drain belongs only to the default sweep. Explicit
    selections never expand into unpicked work.
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
    all_tasks = _tasks_in_service_order(cfg)
    queue = filter_tasks_under(all_tasks, directory, cfg)
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
            known_refs=all_tasks,
            directory=directory,
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
    known_refs: list[TaskRef],
    directory: str | None,
    agent_override: str | None,
    max_tasks: int | None,
    max_steps_per_task: int,
    idle_timeout: float | None,
    max_session: float | None,
) -> list[MegalaunchResult]:
    """The unattended sweep: the operator's own ready `active` / `in_progress`
    work, one launchable step at a time. Draft/paused/terminal tasks are
    ignored and blocked work waits until the post-sweep dependency drain. A
    blocker that names a known task finished by this run is resolved and
    relaunched without a human; every other blocker remains reported and
    parked.
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

        result = _launch_until_stop(
            cfg,
            ref,
            ticket,
            agent_override=agent_override,
            max_steps_per_task=max_steps_per_task,
            idle_timeout=idle_timeout,
            max_session=max_session,
        )
        # A peer can move a queued candidate behind a sweep gate before the
        # exact reread. Such a reclassification was never a launch attempt and
        # must not consume the shared max-tasks budget. A task that launched
        # before later chaining into a gate still counts.
        if result.launched or not result.outcome.startswith("skipped-"):
            attempted += 1
        results.append(result)
    return _drain_satisfied_blockers(
        cfg,
        results,
        known_refs=known_refs,
        directory=directory,
        attempted=attempted,
        max_tasks=max_tasks,
        agent_override=agent_override,
        max_steps_per_task=max_steps_per_task,
        idle_timeout=idle_timeout,
        max_session=max_session,
    )


def _drain_satisfied_blockers(
    cfg: Config,
    results: list[MegalaunchResult],
    *,
    known_refs: list[TaskRef],
    directory: str | None,
    attempted: int,
    max_tasks: int | None,
    agent_override: str | None,
    max_steps_per_task: int,
    idle_timeout: float | None,
    max_session: float | None,
) -> list[MegalaunchResult]:
    """Relaunch blocked work whose named task dependency has finished.

    The current task tree is re-listed on every pass so work created during
    the main sweep is visible. Refs seen earlier remain known after deletion:
    a finished task may legitimately be retired and removed before its
    dependent reaches this drain.

    Each task is drained at most once per run. Its prospective activation is
    validated first, then activation and blocker resolution publish from one
    exact ticket snapshot. A ticket that cannot activate keeps its open ask;
    the combined write also makes the resolved bytes the next launch claim's
    control revision. The explicit per-run set prevents a newly-created
    blocker from relaunching the same task forever.
    """
    # `filter_tasks_under` accepts a human-friendly leading/trailing slash and
    # normalizes it for the main queue. Apply the same normalization to the
    # re-listed drain scope so the two phases cover exactly the same subtree.
    scope_directory = directory.strip("/") if directory is not None else None
    known = {ref.id_slug: ref for ref in known_refs}
    drained_slugs: set[str] = set()

    while max_tasks is None or attempted < max_tasks:
        launched_in_pass = False
        current_refs = _tasks_in_service_order(cfg)
        for current in current_refs:
            known[current.id_slug] = current

        for ref in current_refs:
            if scope_directory is not None and not is_under(
                ref.directory, scope_directory
            ):
                continue
            if ref.id_slug in drained_slugs:
                continue
            try:
                ticket = read_ticket(ref)
            except TicketNotFoundError:
                continue
            except TicketError as exc:
                if not _has_result(results, ref.id_slug):
                    _replace_result(
                        results,
                        _result(ref, "failed", f"unreadable ticket: {exc}"),
                    )
                continue
            if ticket.owner != cfg.current_user or ticket.status != "blocked":
                continue

            blockers = open_blockers(ref.ticket_path)
            if not _has_result(results, ref.id_slug):
                detail = (
                    "; ".join(blocker.reason for blocker in blockers)
                    or "status is blocked"
                )
                _replace_result(
                    results,
                    _result(
                        ref,
                        "skipped-unresolved-blocker",
                        detail,
                        ticket.assignee,
                    ),
                )
            dependency = _finished_blocker_dependency(blockers, known)
            if dependency is None:
                continue
            if max_tasks is not None and attempted >= max_tasks:
                return results

            # Re-acquire the ticket and its blockers as one exact revision.
            # The earlier read established that this task is worth considering;
            # this snapshot is the source lease for the actual activation plus
            # resolution publication, so a peer edit cannot be overlaid.
            audit_path = log_path(cfg)
            activation_snapshot = git.FileMutationRollback.capture(
                (ref.ticket_path, audit_path),
                union_paths=(audit_path,),
            )
            captured = activation_snapshot.originals[ref.ticket_path]
            if captured is None:
                drained_slugs.add(ref.id_slug)
                _replace_result(
                    results,
                    _as_drained(
                        _result(
                            ref,
                            "failed",
                            "ticket disappeared before dependency activation",
                        ),
                        dependency,
                    ),
                )
                continue
            try:
                ticket = Ticket.parse(captured.decode("utf-8"))
                blocker_text = read_blackboard(
                    ref.ticket_path,
                    expected_bytes=captured,
                )
            except (
                OSError,
                UnicodeDecodeError,
                TicketError,
                TaskFileError,
            ) as exc:
                drained_slugs.add(ref.id_slug)
                _replace_result(
                    results,
                    _as_drained(
                        _result(
                            ref,
                            "failed",
                            f"unreadable ticket before dependency activation: {exc}",
                        ),
                        dependency,
                    ),
                )
                continue
            if ticket.owner != cfg.current_user or ticket.status != "blocked":
                _replace_result(
                    results,
                    _result(
                        ref,
                        "failed",
                        "ticket changed before dependency activation; retry",
                        ticket.assignee,
                    ),
                )
                continue
            blockers = [
                blocker
                for blocker in parse_blockers_text(blocker_text)
                if not blocker.resolved
            ]
            dependency = _finished_blocker_dependency(blockers, known)
            if dependency is None:
                detail = (
                    "; ".join(blocker.reason for blocker in blockers)
                    or "status is blocked"
                )
                _replace_result(
                    results,
                    _result(
                        ref,
                        "skipped-unresolved-blocker",
                        detail,
                        ticket.assignee,
                    ),
                )
                continue

            drained_slugs.add(ref.id_slug)
            answer = (
                "Coga megalaunch automatically resolved this blocker after "
                f"dependency {dependency} finished."
            )

            # Validate the prospective activation before either local write.
            # The durable helper then publishes activation and this answer as
            # one exact transaction; a refused activation leaves the blocked
            # ticket and its actionable ask untouched.
            prepared = _prepare_for_launch(cfg, ref, ticket)
            if isinstance(prepared, MegalaunchResult):
                _replace_result(results, _as_drained(prepared, dependency))
                continue
            failure = _activate_for_launch(
                cfg,
                ref,
                ticket,
                log_message=(
                    "activated (blocked → active) — coga megalaunch "
                    f"resolved finished dependency {dependency}"
                ),
                prepared=prepared,
                mutation_snapshot=activation_snapshot,
                blocker_resolution=("system", answer),
            )
            if failure is not None:
                _replace_result(results, _as_drained(failure, dependency))
                continue

            try:
                # The combined write changed both frontmatter and blackboard.
                # Re-read before launch so the strict start claim binds to the
                # exact resolved control revision just published.
                ticket = read_ticket(ref)
            except TicketNotFoundError:
                _replace_result(
                    results,
                    _result(
                        ref,
                        "completed",
                        f"dependency {dependency} finished; task was removed",
                        drained=True,
                    ),
                )
                continue
            except TicketError as exc:
                _replace_result(
                    results,
                    _result(
                        ref,
                        "failed",
                        f"dependency {dependency} finished; unreadable ticket: {exc}",
                        drained=True,
                    ),
                )
                continue

            candidate = _candidate_result(cfg, ref, ticket, explicit=False)
            if candidate is not None:
                _replace_result(results, _as_drained(candidate, dependency))
                continue

            result = _launch_until_stop(
                cfg,
                ref,
                ticket,
                agent_override=agent_override,
                max_steps_per_task=max_steps_per_task,
                idle_timeout=idle_timeout,
                max_session=max_session,
            )
            # The exact launch reread can reclassify a dependency activation
            # just like a main-sweep candidate. Only real attempts share the
            # budget; a late gate skip leaves room for the next dependency.
            if result.launched or not result.outcome.startswith("skipped-"):
                attempted += 1
            _replace_result(results, _as_drained(result, dependency))
            if result.launched:
                launched_in_pass = True
                break

        if not launched_in_pass:
            break
    return results


def _finished_blocker_dependency(
    blockers: list[Blocker], known_refs: dict[str, TaskRef]
) -> str | None:
    """The first exact task ref named by a blocker that is now finished."""
    slugs = sorted(known_refs, key=lambda slug: (-len(slug), slug))
    for blocker in blockers:
        for slug in slugs:
            if not _reason_names_task(blocker.reason, slug):
                continue
            try:
                dependency = read_ticket(known_refs[slug])
            except TicketNotFoundError:
                return slug
            except TicketError:
                continue
            if dependency.status == "done":
                return slug
    return None


def _reason_names_task(reason: str, slug: str) -> bool:
    """True when `reason` contains the complete path-qualified task ref."""
    task_ref_char = r"A-Za-z0-9_./-"
    return re.search(
        rf"(?<![{task_ref_char}]){re.escape(slug)}(?![{task_ref_char}])",
        reason,
    ) is not None


def _has_result(results: list[MegalaunchResult], slug: str) -> bool:
    return any(result.slug == slug for result in results)


def _replace_result(
    results: list[MegalaunchResult], replacement: MegalaunchResult
) -> None:
    """Keep one row per task, its first-seen order, and any prior launch."""
    for index, result in enumerate(results):
        if result.slug == replacement.slug:
            results[index] = replace(
                replacement,
                launched=result.launched or replacement.launched,
            )
            return
    results.append(replacement)


def _as_drained(result: MegalaunchResult, dependency: str) -> MegalaunchResult:
    return MegalaunchResult(
        slug=result.slug,
        outcome=result.outcome,
        detail=f"dependency {dependency} finished; {result.detail}",
        agent=result.agent,
        launched=result.launched,
        drained=True,
    )


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
    operator opted in), then **check** (validate every draft/paused/blocked
    against the `active` view it would get), then **launch** (activate and run
    each).

    Batching the phases means the operator answers every authoring interview
    and sees every unlaunchable pick up front, then the working launches
    proceed without further gating them on a not-yet-ready ticket further down
    the list. Activation itself is *not* batched: it is durable state saying
    work began, so each pick is flipped inside its own launch, after the
    preflights that can still refuse it.
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
                _author_draft(
                    cfg,
                    ref,
                    ticket,
                    agent_override=agent_override,
                )

    # Phase 2 — Check. Validate every picked draft/paused/blocked against the
    # `active` view it would get, and report the ones that still can't launch.
    # Nothing is written: the durable flip happens in phase 3, inside each
    # ticket's own launch. Only refs survive into the launch plan: every
    # lifecycle-dependent decision is re-derived from the fresh phase-3 read,
    # after any earlier picked ticket has finished running.
    launch_plan: list[TaskRef] = []
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
        if ticket.status in TERMINAL_STATUSES:
            results.append(
                _result(
                    ref,
                    "skipped-unlaunchable",
                    f"status is {ticket.status}",
                    ticket.assignee,
                )
            )
            continue
        candidate = _candidate_result(cfg, ref, ticket, explicit=True)
        if candidate is not None:
            results.append(candidate)
            continue
        needs_activation = ticket.status in {"draft", "paused", "blocked"}
        if needs_activation:
            # Prepare only — a blocked ticket also keeps its open asks here for
            # the launch-time preamble. A refusal reads exactly as the durable
            # flip used to report it, with nothing written to disk.
            prepared = _prepare_for_launch(cfg, ref, ticket)
            if isinstance(prepared, MegalaunchResult):
                results.append(prepared)
                continue
            # Activation will freeze the workflow and seed step 1. A ticket
            # with no resulting step cannot be launched.
            if prepared.current_step() is None:
                results.append(
                    _result(
                        ref,
                        "skipped-human-gate",
                        "no current workflow step",
                        ticket.assignee,
                    )
                )
                continue
        launch_plan.append(ref)

    # Phase 3 — Launch. Activate and run the plan one entry at a time,
    # honouring `--max-tasks` over the launches.
    attempted = 0
    for ref in launch_plan:
        if max_tasks is not None and attempted >= max_tasks:
            # `--max-tasks` stops the run here and activation is deferred into
            # each launch, so a pick the run never reaches keeps its
            # draft/paused/blocked status untouched. That is deliberate: an
            # `active` ticket on disk means a session started, and this one
            # never did. Re-pick it to run it.
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
        # Deferring activation widens the window between the check phase and
        # the launch. Reclassify the fresh ticket instead of carrying phase-2
        # status decisions across earlier agent sessions: a concurrent start
        # must not be reactivated, and a newly blocked pick must retain the
        # resume/re-block contract.
        if ticket.status in TERMINAL_STATUSES:
            results.append(
                _result(
                    ref,
                    "skipped-unlaunchable",
                    f"status is {ticket.status}",
                    ticket.assignee,
                )
            )
            continue
        candidate = _candidate_result(cfg, ref, ticket, explicit=True)
        if candidate is not None:
            results.append(candidate)
            continue
        blocked_resume = ticket.status == "blocked"
        needs_activation = ticket.status in {"draft", "paused", "blocked"}
        activation_snapshot: git.FileMutationRollback | None = None
        if needs_activation:
            # Bind preparation, every launch preflight, and the eventual write
            # to one exact ticket revision. Reading the parsed ticket back from
            # the snapshot closes the read/capture gap; mark_active consumes
            # the same snapshot immediately before its write.
            audit_path = log_path(cfg)
            activation_snapshot = git.FileMutationRollback.capture(
                (ref.ticket_path, audit_path),
                union_paths=(audit_path,),
            )
            captured = activation_snapshot.originals[ref.ticket_path]
            if captured is None:
                results.append(
                    _result(ref, "failed", "ticket disappeared before launch")
                )
                continue
            try:
                ticket = Ticket.parse(captured.decode("utf-8"))
                _body, captured_blackboard = split_body(ticket.body)
                assert captured_blackboard is not None
                captured_blockers = [
                    blocker
                    for blocker in parse_blockers_text(captured_blackboard)
                    if not blocker.resolved
                ]
            except (UnicodeDecodeError, TicketError, TaskFileError) as exc:
                results.append(
                    _result(ref, "failed", f"unreadable ticket: {exc}")
                )
                continue
            if ticket.status in TERMINAL_STATUSES:
                results.append(
                    _result(
                        ref,
                        "skipped-unlaunchable",
                        f"status is {ticket.status}",
                        ticket.assignee,
                    )
                )
                continue
            captured_candidate = _candidate_result(
                cfg,
                ref,
                ticket,
                explicit=True,
                blockers=captured_blockers,
            )
            if captured_candidate is not None:
                results.append(captured_candidate)
                continue
            blocked_resume = ticket.status == "blocked"
            needs_activation = ticket.status in {"draft", "paused", "blocked"}
            if not needs_activation:
                # A peer moved the task between the phase-3 read and the exact
                # capture. Refuse this stale selection rather than treating a
                # newly started or closed task as the draft we meant to flip.
                results.append(
                    _result(
                        ref,
                        "failed",
                        "ticket changed before deferred activation; retry",
                        ticket.assignee,
                    )
                )
                continue
        result = _launch_until_stop(
            cfg,
            ref,
            ticket,
            agent_override=agent_override,
            max_steps_per_task=max_steps_per_task,
            idle_timeout=idle_timeout,
            max_session=max_session,
            blocked_resume=blocked_resume,
            activate=needs_activation,
            activation_snapshot=activation_snapshot,
            explicit=True,
        )
        # A selected candidate can cross a current-step, assignee, or terminal
        # gate at the exact reread just like a sweep candidate.  Only a real
        # attempt consumes the shared limit.
        if result.launched or not result.outcome.startswith("skipped-"):
            attempted += 1
        results.append(result)
    return results


def _author_draft(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    agent_override: str | None = None,
) -> None:
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
        agent_override
        or bootstrap_ticket.assignee
        or ticket.agent
        or ticket.assignee
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
    """The tasks the interactive picker offers, ordered like `coga status`.

    Listed as the default status view reads (last updated, newest first, tasks
    with no recorded activity last; ties keep drain order), so the picker and
    the triage view are one list. Display order only: the engine re-derives
    the launch queue from `coga.service_order` and treats the confirmed set as
    a filter, so a numbered pipeline (`1-`, `2-`, `3-`) still runs in number
    order however its rows were displayed.

    Every non-terminal task of any owner — `done` and `canceled` are the only
    exclusions. The picker deliberately does *not* pre-filter for
    launchability: a human-assigned ticket, a stepless one, or an ask-less
    `blocked` ticket all show up, because hiding them silently would let the
    operator pick "everything" and quietly miss real work. Checking a row that
    can't actually launch is not an error — the staged run reports it
    (`skipped-human-gate` / `skipped-unlaunchable`) instead of dropping it.
    Drafts are offered as-is; the prepare phase authors them into shape.
    Unreadable tickets are the only silent skip (the picker offers choices; the
    run reports failures).
    """
    candidates: list[tuple[TaskRef, Ticket]] = []
    for ref in filter_tasks_under(_tasks_in_service_order(cfg), directory, cfg):
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.status in TERMINAL_STATUSES:
            continue
        candidates.append((ref, ticket))
    # The same two-pass sort as `render_status`'s default: newest first, then
    # the no-timestamp bucket last. Both passes are stable, so ties keep the
    # drain order the list was built in.
    updated = last_updated_map(cfg, [ref for ref, _ in candidates])
    candidates.sort(
        key=lambda pair: updated.get(pair[0].id_slug) or datetime.min,
        reverse=True,
    )
    candidates.sort(key=lambda pair: pair[0].id_slug not in updated)
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


def _tasks_in_service_order(cfg: Config) -> list[TaskRef]:
    """All tasks in drain order — oldest first, numbered sub-trees in sequence.

    The key lives in `coga.service_order` so the sweep and `coga status
    --order-by created` read the same order. The picker displays status order
    instead, but a confirmed selection still launches in this drain order.
    """
    return service_order(list_tasks(cfg), first_activity_map(cfg))


def _candidate_result(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    explicit: bool = False,
    blockers: list[Blocker] | None = None,
) -> MegalaunchResult | None:
    if blockers is None:
        blockers = open_blockers(ref.ticket_path)
    if ticket.status == "blocked":
        # The initial unattended pass does not resume a blocked ticket. Its
        # terminal dependency drain may later resolve and activate one whose
        # blocker names a finished task. An explicit pick *is* a separate
        # human act: the launch activates it and the composed prompt gains the
        # resolve-or-re-block preamble, so only an ask-less blocked ticket
        # (nothing to resolve) stays unlaunchable.
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

    if ticket.assignee not in cfg.agents:
        return _result(
            ref,
            "skipped-human-gate",
            f"assignee {ticket.assignee or 'unassigned'} is not a configured agent",
            ticket.assignee,
        )

    # A draft has no current step yet — activation freezes the workflow and
    # seeds step 1, so its step gate runs post-activation in
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
    activate: bool = False,
    activation_snapshot: git.FileMutationRollback | None = None,
    explicit: bool = False,
) -> MegalaunchResult:
    # `ticket` is `active` / `in_progress` unless `activate` is set — the sweep
    # only reaches here for ready work, while the selection path hands over a
    # still-unactivated draft/paused/blocked pick and lets the first step below
    # flip it, after the preflights. `blocked_resume` marks a
    # ticket that was blocked when picked: the composed prompt carries the
    # resolve-or-re-block preamble off the blackboard's still-open asks, and an
    # exit that leaves an ask open returns it to `blocked` below.
    launched = False
    first_step = True
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

        # Active/resumed work has no earlier selection snapshot. Re-read it
        # from exact bytes before deriving routing or inputs, then retain those
        # raw bytes as the compare-and-swap source revision. This accepts
        # harmless non-canonical YAML formatting without weakening the guard.
        preflight_source_bytes: bytes | None = None
        if not activate:
            try:
                preflight_source_bytes = ref.ticket_path.read_bytes()
                ticket = Ticket.parse(preflight_source_bytes.decode("utf-8"))
                _body, exact_blackboard = split_body(ticket.body)
                assert exact_blackboard is not None
                exact_blockers = [
                    blocker
                    for blocker in parse_blockers_text(exact_blackboard)
                    if not blocker.resolved
                ]
            except FileNotFoundError:
                return _result(
                    ref,
                    "failed",
                    "ticket disappeared before launch",
                    ticket.assignee,
                    launched=launched,
                )
            except (UnicodeDecodeError, TicketError, TaskFileError) as exc:
                return _result(
                    ref,
                    "failed",
                    f"unreadable ticket: {exc}",
                    ticket.assignee,
                    launched=launched,
                )

            # The outer queue scan is only a candidate hint. A peer may change
            # owner, status, blockers, or the current workflow step before this
            # exact reread, so reapply every sweep gate to these same bytes
            # before deriving a prompt or lifecycle mutation from them.
            if not explicit and ticket.owner != cfg.current_user:
                return _result(
                    ref,
                    "skipped-human-gate",
                    f"owner {ticket.owner or 'unassigned'} is not current "
                    f"operator {cfg.current_user}",
                    ticket.assignee,
                    launched=launched,
                )
            if not explicit and ticket.status not in {
                "active",
                "in_progress",
                "blocked",
            }:
                return _result(
                    ref,
                    "skipped-unlaunchable",
                    f"status is {ticket.status}",
                    ticket.assignee,
                    launched=launched,
                )
            if ticket.status in TERMINAL_STATUSES:
                return _result(
                    ref,
                    "skipped-unlaunchable",
                    f"status is {ticket.status}",
                    ticket.assignee,
                    launched=launched,
                )
            exact_candidate = _candidate_result(
                cfg,
                ref,
                ticket,
                explicit=explicit,
                blockers=exact_blockers,
            )
            if exact_candidate is not None:
                return replace(exact_candidate, launched=launched)

        if ticket.assignee not in cfg.agents:
            return _result(
                ref,
                "completed",
                f"handed off to {ticket.assignee or 'unassigned'}",
                ticket.assignee,
                launched=launched,
            )
        # The override applies only to the task's first launched step, so
        # `other-agent` rotation on later steps still lands on the ticket's
        # resolved assignee.
        launch_assignee = (
            (agent_override or ticket.assignee) if first_step else ticket.assignee
        )
        first_step = False

        # A deferred activation belongs to the first step only. Preflight the
        # prospective `active` view, materializing the exact `in_progress`
        # prompt, environment, and agent this launch will use. Commit the flip
        # only once every refusal below has passed, so a ticket whose session
        # never starts is never left claiming it did.
        preflight_view = ticket
        prepared_activation: Ticket | None = None
        if activate:
            prepared = _prepare_for_launch(cfg, ref, ticket)
            if isinstance(prepared, MegalaunchResult):
                return prepared
            preflight_view = prepared
            prepared_activation = prepared

        prepared_launch = _preflight_agent_launch(
            cfg,
            ref,
            preflight_view,
            launch_assignee,
            source_ticket_bytes=preflight_source_bytes,
        )
        if isinstance(prepared_launch, str):
            return _result(
                ref,
                "failed",
                prepared_launch,
                launch_assignee,
                launched=launched,
            )

        if activate:
            activate = False
            failure = _activate_for_launch(
                cfg,
                ref,
                ticket,
                prepared=prepared_activation,
                mutation_snapshot=activation_snapshot,
            )
            if failure is not None:
                return failure

        # Activation sync can spend long enough fetching/publishing for a peer
        # to edit or complete the ticket. Bind the following start write to the
        # exact active bytes that the preflight saw; never overlay that peer
        # revision with this loop's stale in-memory ticket. The same guard also
        # closes the preflight window for an already-active sweep candidate.
        prior_start_status = ticket.status
        audit_path = log_path(cfg)
        start_snapshot = git.FileMutationRollback.capture(
            (ref.ticket_path, audit_path),
            union_paths=(audit_path,),
        )
        if (
            start_snapshot.originals[ref.ticket_path]
            != prepared_launch.source_ticket_bytes
        ):
            return _result(
                ref,
                "failed",
                "ticket changed after launch preflight; retry",
                launch_assignee,
                launched=launched,
            )
        try:
            mark_in_progress(
                cfg,
                ref,
                prepared_launch.ticket,
                actor="megalaunch",
                log_message=(
                    "started (active → in_progress) via coga megalaunch"
                    if prior_start_status == "active"
                    else "claimed in_progress resume via coga megalaunch"
                ),
                echo=None,
                mutation_snapshot=start_snapshot,
                state_guard=(
                    git.ticket_state_guard(
                        cfg,
                        ref.ticket_path,
                        expected_ticket_bytes=(
                            prepared_launch.source_ticket_bytes
                        ),
                        allow_launch_claim_acquisition=True,
                    )
                    if cfg.git_enabled
                    else None
                ),
                strict_state_guard=cfg.git_enabled,
                strict_state_sync=cfg.git_enabled,
            )
        except TaskValidationError as exc:
            git.restore_files_under_barrier(cfg, start_snapshot)
            return _result(ref, "failed", str(exc), ticket.assignee)
        except git.UncertainFeaturePublicationError as exc:
            return _result(
                ref,
                "failed",
                "launch claim publication outcome is uncertain; generated "
                f"local state retained for reconciliation — {exc}",
                ticket.assignee,
            )
        except git.GitError as exc:
            git.restore_files_under_barrier(cfg, start_snapshot)
            return _result(
                ref,
                "failed",
                f"launch claim publication refused: {exc}; retry",
                ticket.assignee,
            )
        # `mark_in_progress` includes synchronous Git publication. A peer can
        # replace, complete, or claim the ticket while that network boundary
        # is in flight, after our pre-write CAS has already succeeded. Spawn
        # only if the live file is still the exact claimed revision whose
        # prompt, environment, and agent were materialized above.
        try:
            post_start_ticket_bytes = ref.ticket_path.read_bytes()
        except FileNotFoundError:
            post_start_ticket_bytes = None
        expected_started_bytes = prepared_launch.ticket.render().encode("utf-8")
        if post_start_ticket_bytes != expected_started_bytes:
            return _result(
                ref,
                "failed",
                "ticket changed during start publication; current state "
                "retained for safe resume; retry",
                launch_assignee,
                launched=launched,
            )

        def revalidate_launch_claim() -> None:
            _revalidate_launch_claim_before_spawn(
                cfg,
                ref,
                expected_started_bytes=expected_started_bytes,
            )

        def admit_released_launch_claim() -> None:
            _admit_launch_claim_after_release(
                cfg,
                ref,
                expected_started_bytes=expected_started_bytes,
            )

        before = prepared_launch.ticket
        try:
            agent = prepared_launch.agent
            # A normal interactive launch: the REPL streams to the console
            # under the PTY watcher, and the done-sentinel (`coga bump` /
            # `mark done` / `mark canceled` / `block`) releases it — never
            # headless `-p`, which
            # buffers all output until the run ends.
            session = spawn_agent_session(
                cfg,
                ref,
                before,
                agent,
                env=prepared_launch.env,
                actor="megalaunch",
                log_message="launched via coga megalaunch",
                name=before.title or "",
                idle_timeout=idle_timeout,
                max_session=max_session,
                launch_context="megalaunch",
                label="Megalaunch",
                warn_blackboard=True,
                composed_prompt=prepared_launch.prompt,
                validate_before_spawn=revalidate_launch_claim,
                validate_after_spawn=revalidate_launch_claim,
                after_spawn_release=(
                    admit_released_launch_claim if cfg.git_enabled else None
                ),
                record_launch_on_spawn=True,
            )
        except _LaunchClaimRefused as exc:
            return _result(
                ref,
                "failed",
                f"{exc}; current state retained for safe resume; retry",
                launch_assignee,
                launched=launched,
            )
        except (ComposeError, ConfigError, SecretError) as exc:
            return _result(ref, "failed", str(exc), launch_assignee)
        except git.GitError as exc:
            return _result(
                ref,
                "failed",
                f"launch admission publication barrier unavailable: {exc}",
                launch_assignee,
            )
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


# The refusals `prepare_active` raises before `mark_active` writes anything.
# `TaskValidationError` is deliberately not one of them: it comes from the
# post-write `assert_task_valid`, so it belongs to the commit half alone.
_PREPARE_ACTIVE_ERRORS = (
    WorkflowMissing,
    WorkflowError,
    RequiredExtensionMissing,
    BlackboardNeedsSynthesis,
)


def _activation_refusal(
    ref: TaskRef,
    ticket: Ticket,
    prior: str,
    exc: Exception,
) -> MegalaunchResult:
    """Map a refused activation to the loud result the sweep reports.

    Shared by the prepare and commit halves so a refusal reads identically
    whichever side of the durable write raised it.
    """
    if isinstance(exc, WorkflowMissing):
        return _result(
            ref,
            "skipped-unlaunchable",
            f"{prior} with no workflow — set `workflow:` in ticket.md or run "
            f"`coga ticket {ref.id_slug}`",
            ticket.assignee,
        )
    if isinstance(exc, WorkflowError):
        return _result(
            ref,
            "skipped-unlaunchable",
            f"`workflow:` ref could not be frozen — {exc}",
            ticket.assignee,
        )
    if isinstance(exc, RequiredExtensionMissing):
        names = ", ".join(repr(f) for f in exc.fields)
        return _result(
            ref,
            "skipped-unlaunchable",
            f"required extension field(s) empty: {names}",
            ticket.assignee,
        )
    if isinstance(exc, BlackboardNeedsSynthesis):
        return _result(
            ref,
            "skipped-unlaunchable",
            f"blackboard needs synthesis before first launch: {exc.reason}",
            ticket.assignee,
        )
    return _result(ref, "failed", str(exc), ticket.assignee)


def _prepare_for_launch(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
) -> Ticket | MegalaunchResult:
    """The `active` view a picked ticket *would* get, without writing it.

    The prepare half of the activation: `prepare_active` on a throwaway copy,
    so every refusal it can raise — and every preflight run against the view it
    returns — happens before anything durable exists. Returns the prospective
    ticket, or the refusal result to report instead.

    Callers must re-run this after any re-read of the ticket rather than
    carrying the prepared view across one: it is an uncommitted mutation, and a
    fresh `read_ticket` discards it.
    """
    prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    prior = ticket.status
    try:
        prepare_active(cfg, ref, prospective)
    except _PREPARE_ACTIVE_ERRORS as exc:
        return _activation_refusal(ref, ticket, prior, exc)
    return prospective


def _activate_for_launch(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    log_message: str | None = None,
    prepared: Ticket | None = None,
    mutation_snapshot: git.FileMutationRollback | None = None,
    blocker_resolution: tuple[str, str] | None = None,
) -> MegalaunchResult | None:
    """Commit a picked or dependency-drained ticket to `active`.

    Mirrors `coga launch`'s inline auto-activation, but returns a loud result
    instead of exiting the process — one bad task must not kill the sweep.
    `mark_active` mutates `ticket` in place (status, frozen workflow, seeded
    step), so the caller's launch loop continues off the same object.

    The durable half. A deferred picker launch supplies the exact prospective
    ticket its preflight saw plus a mutation snapshot of the source revision.
    `mark_active` therefore sees an already-prepared `active` ticket (so it
    cannot freeze a changed workflow definition) and refuses immediately
    before writing if a peer changed the ticket. A dependency drain also
    supplies an actor/answer pair: after activation validates and writes, its
    blocker update joins the same snapshot and exact control publication. Thus
    the next launch claim leases resolved bytes rather than a local-only edit.
    """
    prior = ticket.status
    strict_source_bytes: bytes | None = None
    strict_activation = (
        cfg.git_enabled
        and prepared is not None
        and mutation_snapshot is not None
    )
    if blocker_resolution is not None and (
        prepared is None or mutation_snapshot is None
    ):
        return _result(
            ref,
            "failed",
            "dependency resolution requires an exact activation snapshot",
            ticket.assignee,
        )
    if strict_activation:
        strict_source_bytes = mutation_snapshot.originals.get(ref.ticket_path)
        if strict_source_bytes is None:
            return _result(
                ref,
                "failed",
                "ticket disappeared before deferred activation",
                ticket.assignee,
            )
    if prepared is not None:
        ticket.frontmatter = dict(prepared.frontmatter)
        ticket.body = prepared.body
    try:
        mark_active(
            cfg,
            ref,
            ticket,
            actor="megalaunch",
            log_message=(
                log_message
                or f"activated ({prior} → active) — explicit megalaunch pick"
            ),
            echo=None,
            sync_state=not strict_activation and blocker_resolution is None,
            mutation_snapshot=mutation_snapshot,
        )
        if blocker_resolution is not None:
            assert mutation_snapshot is not None
            generated = mutation_snapshot.generated
            if generated is None or generated.get(ref.ticket_path) is None:
                raise git.FeaturePublicationError(
                    "activation did not arm dependency-resolution ticket bytes"
                )
            actor, answer = blocker_resolution
            try:
                with git.state_publication_barrier(cfg):
                    resolved = resolve_open_blockers(
                        ref.ticket_path,
                        actor=actor,
                        answer=answer,
                        expected_bytes=generated[ref.ticket_path],
                        after_write=lambda written: mutation_snapshot.arm(
                            {ref.ticket_path: written}
                        ),
                    )
            except (OSError, UnicodeError, TaskFileError) as exc:
                raise git.FeaturePublicationError(
                    f"could not resolve dependency blocker: {exc}"
                ) from exc
            if not resolved:
                raise git.FeaturePublicationError(
                    "dependency blocker changed before its guarded resolution"
                )
        if strict_activation:
            assert mutation_snapshot is not None
            assert strict_source_bytes is not None
            git.sync_task_state(
                cfg,
                ref.path,
                message=f"Ticket: {ref.id_slug} — active",
                guard=git.ticket_state_guard(
                    cfg,
                    ref.ticket_path,
                    expected_ticket_bytes=strict_source_bytes,
                ),
                generated_paths=mutation_snapshot.generated,
                raise_state_regression=True,
                raise_git_error=True,
            )
    except git.UncertainFeaturePublicationError as exc:
        return _activation_refusal(
            ref,
            ticket,
            prior,
            git.FeaturePublicationError(
                "activation publication outcome is uncertain; generated "
                f"local state retained for reconciliation — {exc}"
            ),
        )
    except (
        *_PREPARE_ACTIVE_ERRORS,
        TaskValidationError,
        git.GitError,
    ) as exc:
        if (
            isinstance(exc, (TaskValidationError, git.GitError))
            and mutation_snapshot is not None
        ):
            git.restore_files_under_barrier(cfg, mutation_snapshot)
        return _activation_refusal(ref, ticket, prior, exc)
    return None


def _revalidate_launch_claim_before_spawn(
    cfg: Config,
    ref: TaskRef,
    *,
    expected_started_bytes: bytes,
) -> None:
    """Re-prove one exact local/control claim at the actual PTY boundary.

    Strict claim publication closes the race between preflight and the first
    control push, and a published generation is not automatically reclaimable
    by another megalaunch. Still reread the local ticket and every effective
    control push destination from a private fetch immediately before
    ``run_with_done_marker`` so arbitrary peer edits after publication cannot
    reach spawn. Exact ticket bytes bind the proof to the preflighted prompt as
    well as the generation.

    Refusal deliberately leaves the pending ``in_progress`` claim untouched.
    Ordinary ``coga launch`` refuses that visible held-child state; only the
    post-release admission callback turns it into a plain generation that can
    be recovered explicitly.
    """
    def require_local_claim() -> None:
        try:
            local_bytes = ref.ticket_path.read_bytes()
        except OSError as exc:
            raise _LaunchClaimRefused(
                f"launch claim could not be read before agent spawn: {exc}"
            ) from exc
        if local_bytes != expected_started_bytes:
            raise _LaunchClaimRefused(
                "launch claim changed locally before agent spawn"
            )

    require_local_claim()
    if not cfg.git_enabled:
        return

    try:
        root = git._toplevel(ref.path)
        if root is None:
            raise git.GitError(
                "strict launch-claim verification requires a Git checkout"
            )
        guard = git.ticket_state_guard(
            cfg,
            ref.ticket_path,
            expected_ticket_bytes=expected_started_bytes,
        )
        for push_url in git._remote_push_urls(root, cfg.git_remote):
            control_tip = git._fetch_branch_oid(
                root,
                push_url,
                cfg.git_control_branch,
            )
            guard(control_tip)
    except git.StateRegressionError as exc:
        raise _LaunchClaimRefused(
            f"launch claim changed on control before agent spawn: {exc}"
        ) from exc
    except git.GitError as exc:
        raise _LaunchClaimRefused(
            f"launch claim could not be verified before agent spawn: {exc}"
        ) from exc
    # Fetching control may take long enough for a local ordinary launch to
    # update the blackboard. Keep the last filesystem action before returning
    # to the PTY call an exact local reread too.
    require_local_claim()


def _admit_launch_claim_after_release(
    cfg: Config,
    ref: TaskRef,
    *,
    expected_started_bytes: bytes,
) -> None:
    """Publish pending-to-admitted only after the held child is released.

    The supervisor calls this while retaining the same-checkout publication
    barrier that covered the final remote proof and gate write. Cross-checkout
    publishers see the visible ``pending:`` claim and refuse every replacement;
    this exact one-field transition is the sole exception. Once it lands, the
    child can already execute, so ordinary lifecycle changes may proceed.
    """
    if not cfg.git_enabled:
        return
    try:
        current_bytes = ref.ticket_path.read_bytes()
    except OSError as exc:
        raise _LaunchClaimRefused(
            f"pending launch claim could not be read after child release: {exc}"
        ) from exc
    if current_bytes != expected_started_bytes:
        raise _LaunchClaimRefused(
            "pending launch claim changed locally during child release"
        )
    try:
        ticket = Ticket.parse(current_bytes.decode("utf-8"))
    except (UnicodeDecodeError, TicketError) as exc:
        raise _LaunchClaimRefused(
            f"pending launch claim became unreadable after child release: {exc}"
        ) from exc
    generation = ticket.launch_generation
    if not pending_launch_generation(generation):
        raise _LaunchClaimRefused(
            "launch claim was not pending after child release"
        )
    assert generation is not None

    admitted_generation = admitted_launch_generation(generation)
    released_ticket = Ticket(
        frontmatter=dict(ticket.frontmatter),
        body=ticket.body,
    )
    released_ticket.frontmatter["launch_generation"] = (
        released_generation_from_pending(generation)
    )
    try:
        # Record release before attempting its remote publication. If that
        # publication fails, this local-only form is the durable capability
        # that lets an explicit ordinary launch safely reconcile and recover.
        released_ticket.write(ref.ticket_path)
    except OSError as exc:
        raise _LaunchClaimRefused(
            "released launch admission could not be recorded locally; "
            f"manual reconciliation is required: {exc}"
        ) from exc

    audit_path = log_path(cfg)
    mutation = git.FileMutationRollback.capture(
        (ref.ticket_path, audit_path),
        union_paths=(audit_path,),
    )
    try:
        mutation.require_unchanged(ref.ticket_path)
        ticket.frontmatter["launch_generation"] = admitted_generation
        admitted_bytes = ticket.render().encode("utf-8")
        ticket.write(ref.ticket_path)
        mutation.arm({ref.ticket_path: admitted_bytes})
        # The supervisor already holds ``state_publication_barrier`` through
        # this callback. Re-entering it would deadlock, so use the shared
        # publisher's narrow no-barrier form for this exact transition.
        git._sync_paths_without_barrier(
            cfg,
            ref.path,
            (ref.ticket_path,),
            message=f"Ticket: {ref.id_slug} — launch admitted",
            guard=git.ticket_state_guard(
                cfg,
                ref.ticket_path,
                expected_ticket_bytes=current_bytes,
                allow_launch_claim_admission=True,
            ),
            generated_paths=mutation.generated,
            raise_state_regression=True,
            raise_git_error=True,
            allow_launch_claim_admission=True,
        )
    except git.UncertainFeaturePublicationError as exc:
        refused = mutation.restore()
        detail = ""
        if refused:
            paths = ", ".join(str(path) for path in refused)
            detail = f"; released witness could not be restored from {paths}"
        raise _LaunchClaimRefused(
            "launch-admission publication outcome is uncertain; admitted "
            "child was terminated and released local state was retained for "
            f"`coga launch {ref.id_slug}` reconciliation — {exc}{detail}"
        ) from exc
    except git.GitError as exc:
        refused = mutation.restore()
        detail = ""
        if refused:
            paths = ", ".join(str(path) for path in refused)
            detail = f"; generated bytes could not be restored from {paths}"
        raise _LaunchClaimRefused(
            "launch admission could not be published; admitted child was "
            "terminated and released local state was retained for "
            f"`coga launch {ref.id_slug}` reconciliation: {exc}{detail}"
        ) from exc
    except (OSError, ValueError) as exc:
        refused = mutation.restore()
        detail = ""
        if refused:
            paths = ", ".join(str(path) for path in refused)
            detail = f"; generated bytes could not be restored from {paths}"
        raise _LaunchClaimRefused(
            f"launch admission could not be recorded: {exc}{detail}"
        ) from exc


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


def _chain_stop_result(
    cfg: Config, ref: TaskRef, after: Ticket
) -> MegalaunchResult | None:
    """Terminal chain state after an agent step, or None to keep chaining."""
    if after.status == "blocked":
        blockers = open_blockers(ref.ticket_path)
        detail = "; ".join(blocker.reason for blocker in blockers) or "blocked"
        return _result(ref, "blocked", detail, after.assignee, launched=True)
    if after.status == "canceled":
        return _result(
            ref,
            "canceled",
            "task canceled",
            after.assignee,
            launched=True,
        )
    if after.status in TERMINAL_STATUSES:
        return _result(
            ref,
            "completed",
            f"task {after.status}",
            after.assignee,
            launched=True,
        )
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
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    launch_assignee: str | None,
    *,
    source_ticket_bytes: bytes | None = None,
) -> _PreparedAgentLaunch | str:
    try:
        agent = cfg.agent_type(launch_assignee or "")
    except ConfigError as exc:
        return str(exc)
    # A not-yet-activated pick arrives as its prospective `active` view. Keep
    # the launch boundary strict so malformed or concurrently changed states
    # cannot reach the agent spawn path.
    if ticket.status not in {"active", "in_progress"}:
        return f"status is {ticket.status}; expected active or in_progress"
    if ticket.status == "in_progress" and ticket.launch_generation is not None:
        if pending_launch_generation(ticket.launch_generation):
            return (
                "ticket already carries a pending megalaunch admission; its "
                "held child must be released or the claim reconciled before "
                "another session can start"
            )
        if released_launch_generation(ticket.launch_generation):
            return (
                "ticket carries a released megalaunch admission awaiting "
                f"reconciliation — run `coga launch {ref.id_slug}` to recover"
            )
        return (
            "ticket already carries a published megalaunch claim; refusing "
            "an automatic concurrent resume — use `coga launch "
            f"{ref.id_slug}` to recover it explicitly"
        )
    if shutil.which(agent.cli) is None:
        return agent_cli_missing_message(agent.cli)
    expected_source_bytes = (
        ticket.render().encode("utf-8")
        if source_ticket_bytes is None
        else source_ticket_bytes
    )
    launch_ticket = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    if launch_ticket.status == "active":
        launch_ticket.frontmatter["status"] = "in_progress"
    generation = str(uuid4())
    launch_ticket.frontmatter["launch_generation"] = (
        f"{PENDING_LAUNCH_GENERATION_PREFIX}{generation}"
        if cfg.git_enabled
        else generation
    )
    try:
        prompt = compose_prompt(
            cfg, ref, launch_ticket, launch_context="megalaunch"
        )
        env = build_supervised_step_env(
            build_launch_env(cfg, launch_ticket.secrets),
            task_path=ref.path,
            step=launch_ticket.step,
        )
    except FileNotFoundError as exc:
        return missing_launch_file_message(exc)
    except (ConfigError, ComposeError, SecretError) as exc:
        return str(exc)
    if cfg.git_enabled and check_git_remote(cfg.git_remote).ok:
        auth = check_git_auth(cfg.git_remote)
        if not auth.ok:
            return f"git push access unavailable: {auth.detail}"
    return _PreparedAgentLaunch(
        ticket=launch_ticket,
        source_ticket_bytes=expected_source_bytes,
        agent=agent,
        env=env,
        prompt=prompt,
    )


def _result(
    ref: TaskRef,
    outcome: MegalaunchOutcome,
    detail: str,
    agent: str | None = None,
    *,
    launched: bool = False,
    drained: bool = False,
) -> MegalaunchResult:
    return MegalaunchResult(
        slug=ref.id_slug,
        outcome=outcome,
        detail=detail,
        agent=agent,
        launched=launched,
        drained=drained,
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
        "drained",
        "completed",
        "canceled",
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


def write_run_summary(
    cfg: Config,
    blackboard_path: Path,
    run: MegalaunchRun,
) -> None:
    """Write the latest run summary while trimming old megalaunch noise."""
    update_blackboard_under_barrier(
        cfg,
        blackboard_path,
        lambda region: trim_megalaunch_blackboard_text(
            region,
            render_run_summary(run),
        ),
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
