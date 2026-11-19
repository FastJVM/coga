"""Sequential console launcher for launchable, agent-owned Coga work.

The default sweep covers the operator's `active` and `in_progress` tickets
(`--owner <name>` retargets it to that owner's tickets, `--all-owners` to
every owner's; the operator running megalaunch stays `current_user`):
`active` work starts, `in_progress` work — a session another process started
that has since crashed or been torn down mid-step — resumes, exactly like a
manual `coga launch <slug>`. After that pass, a fixed-point dependency drain
re-lists the same owner's blocked tickets: when an open blocker names a known
task that is now done (or was deleted after finishing), megalaunch resolves
that ask with an explicit automatic answer. The dependent relaunches only
when no open asks remain. Each
drain launch restarts the walk; a full pass with no launch ends the run.

An **explicit selection** (the `--pick` picker or `--relaunch`) runs only the
named tasks — whatever their owner; the owner flags only shape the list the
picker offers, which defaults to the operator's own tickets — and reaches wider —
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
import typer
import os
import signal
import sys
import time

if os.name == "posix":
    import select
    import termios
    import tty

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from coga import git, notification
from coga.atomicio import atomic_write_bytes
from coga.authoring import invoke_ticket_authoring, resolve_authoring_agent
from coga.blackboard import (
    Blocker,
    open_blockers,
    parse_blockers_text,
    resolve_blockers_text,
    update_blackboard_under_barrier,
)
from coga.claimed_session import (
    activate_claimed_ticket,
    snapshot_ticket_bytes as _ticket_bytes,
    snapshot_log_bytes as _log_bytes,
    restore_owned_ticket,
)
from coga.launch import run_claimed_agent_session, interactive_stdio_has_tty
from coga.session_limits import resolve_idle_timeout, resolve_max_session
from coga.config import Config, ConfigError, load_config
from coga.logfile import append_log, first_activity_map
from coga.lifecycle import TERMINAL_STATUSES
from coga.mark import (
    PREPARE_ACTIVE_ERRORS as _PREPARE_ACTIVE_ERRORS,
    reblock_unresolved_resume,
    BlackboardNeedsSynthesis,
    MainAgentUnavailable,
    RequiredExtensionMissing,
    WorkflowMissing,
    prepare_active,
)
from coga.repl_supervisor import unsignalled_advance_warning
from coga.workflow import WorkflowError
from coga.taskfile import TaskFileError, read_blackboard, split_body
from coga.service_order import service_order
from coga.tasks import (
    TaskNotFoundError,
    TaskRef,
    filter_tasks_under,
    is_under,
    list_tasks,
    read_ticket,
    resolve_bootstrap,
    UnknownDirectoryError,
)
from coga.ticket import Ticket, TicketError, TicketNotFoundError
from coga.views import last_updated_map
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.text import Text


# Queue-owned idle backstop for spawned REPLs; recurring owns its own.
QUEUE_IDLE_TIMEOUT_SECONDS = 900.0


class MegalaunchError(Exception):
    """Megalaunch cannot run at all — e.g. no TTY for the interactive REPLs."""


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
    # The agent failed to start: every megalaunch loop stops after this row.
    stops_run: bool = False


@dataclass(frozen=True)
class MegalaunchRun:
    started_at: datetime
    agent_override: str | None = None
    directory: str | None = None
    selection: tuple[str, ...] | None = None
    results: list[MegalaunchResult] = field(default_factory=list)
    # Whose tickets a non-default sweep covered: an `--owner` name, or
    # "every owner" for `--all-owners`. `None` for the default (operator's
    # own) sweep and for explicit selections.
    owner_scope: str | None = None

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
    owner: str | None = None,
    all_owners: bool = False,
    max_steps_per_task: int = 8,
) -> MegalaunchRun:
    """Attempt launchable `active` and `in_progress` tasks sequentially.

    `directory` narrows the sweep to that `tasks/` sub-tree (nested tasks
    included), same semantics as `coga status <dir>` — an unknown directory
    raises `UnknownDirectoryError` rather than sweeping nothing silently.

    `agent_override` runs picked-draft authoring interviews and launches swept
    agent-held tickets with that configured agent type instead of the default
    authoring agent / each ticket's derived operator. It is ephemeral and applies
    only to authoring plus the first launched step, so `other-agent` rotation on
    later steps still lands on the ticket's configured peer. Unlike an explicit
    `coga launch --agent`, megalaunch keeps its independent human gate: steps the
    workflow hands to the owner still skip, override or not.

    `owner` / `all_owners` choose whose tickets the sweep covers (see
    `resolve_owner_filter`): the operator's own by default, `owner`'s
    instead, or every owner's. One target owner gates the queue scan, the
    exact launch reread, and both dependency-drain checks, so the reread can
    never reject what the scan queued. They are refused with `selection`,
    whose picks already are explicit.

    `selection` (exact `id_slug`s) switches to explicit mode: only the named
    tasks run, whatever their owner, and the run is staged so every human-in-the-loop
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
    if selection is not None and (owner is not None or all_owners):
        raise MegalaunchError(
            "--owner and --all-owners shape the picker list or the sweep; an "
            "explicit selection already names its tasks."
        )
    owner_filter = resolve_owner_filter(cfg, owner=owner, all_owners=all_owners)
    if not interactive_stdio_has_tty():
        raise MegalaunchError(
            "megalaunch spawns interactive agent REPLs and requires a TTY "
            "(stdin and stdout must both be terminals). Run it from a real "
            "shell."
        )
    started_at = datetime.now(timezone.utc)
    # Liveness backstops for the spawned REPLs, resolved once per sweep with
    # the shared precedence (env override > [launch] config) over the queue's
    # own idle default. Human keystrokes count as activity, so an attended
    # session is only torn down when it is genuinely idle.
    idle_timeout = resolve_idle_timeout(cfg, default=QUEUE_IDLE_TIMEOUT_SECONDS)
    max_session = resolve_max_session(cfg)

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
            owner_filter=owner_filter,
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
        owner_scope=(
            "every owner" if all_owners else owner
        ),
    )


def resolve_owner_filter(
    cfg: Config, *, owner: str | None = None, all_owners: bool = False
) -> str | None:
    """The one owner every sweep gate compares against; `None` = every owner.

    The default is the operator (`cfg.current_user`). `owner` retargets the
    filter to another accountable human's tickets — a free string, since there
    is no user registry, so an unknown name simply matches nothing.
    `all_owners` drops the filter (owner-less tickets included). The two are
    mutually exclusive. The filter reads the ticket's `owner:` only, never the
    current step's assignee.
    """
    if owner is not None and all_owners:
        raise MegalaunchError("--owner and --all-owners cannot be combined.")
    if all_owners:
        return None
    return owner if owner is not None else cfg.current_user


def _owner_in_scope(ticket: Ticket, owner_filter: str | None) -> bool:
    return owner_filter is None or ticket.owner == owner_filter


def _run_sweep(
    cfg: Config,
    queue: list[TaskRef],
    *,
    known_refs: list[TaskRef],
    directory: str | None,
    owner_filter: str | None,
    agent_override: str | None,
    max_tasks: int | None,
    max_steps_per_task: int,
    idle_timeout: float | None,
    max_session: float | None,
) -> list[MegalaunchResult]:
    """The unattended sweep: the target owner's ready `active` / `in_progress`
    work (the operator's own by default), one launchable step at a time. Draft/paused/terminal tasks are
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

        # Scope the sweep to the target owner's work — the running operator's
        # own unless `--owner`/`--all-owners` said otherwise. On a shared repo
        # a daily sweep must not launch other people's tickets, so a ticket
        # outside the filter is skipped silently — it never enters `results`,
        # so other owners' work doesn't inflate the summary counts.
        # `ticket.owner` is `None` when the field is absent, so owner-less
        # tickets are excluded by any named filter. Part 1 guarantees
        # `current_user` is a real configured name, never a guess, so the
        # default filter is trustworthy for unattended runs.
        if not _owner_in_scope(ticket, owner_filter):
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
            owner_filter=owner_filter,
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
        if result.stops_run:
            # An agent that cannot start is an environment problem every
            # later launch would hit too: end the run, drain included.
            return results
    return _drain_satisfied_blockers(
        cfg,
        results,
        known_refs=known_refs,
        directory=directory,
        owner_filter=owner_filter,
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
    owner_filter: str | None,
    attempted: int,
    max_tasks: int | None,
    agent_override: str | None,
    max_steps_per_task: int,
    idle_timeout: float | None,
    max_session: float | None,
) -> list[MegalaunchResult]:
    """Relaunch blocked work whose named task dependency has finished.

    Only tickets inside `owner_filter` (the sweep's target owner) drain. The
    drain answers nothing on anyone's behalf — it resolves only blockers whose
    named dependency is already done — so it follows the sweep's owner.

    The current task tree is re-listed on every pass so work created during
    the main sweep is visible. Refs seen earlier remain known after deletion:
    a finished task may legitimately be retired and removed before its
    dependent reaches this drain.

    Partial resolutions publish from an exact snapshot, keeping the task
    blocked. Once every remaining ask is satisfied, prospective activation
    validates first, then activation and resolution publish together. A ticket
    that cannot activate keeps its remaining asks. The resolved bytes become
    the next launch claim's control revision. Each task may launch from the
    drain at most once, preventing a new blocker from relaunching it forever.
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
            if not _owner_in_scope(ticket, owner_filter) or ticket.status != "blocked":
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
                        _operator_name(cfg, ref, ticket),
                    ),
                )
            resolutions = _finished_blocker_dependencies(blockers, known)
            if not resolutions:
                continue
            dependency = ", ".join(dict.fromkeys(resolutions.values()))
            if max_tasks is not None and attempted >= max_tasks:
                return results

            # Re-acquire the ticket and its blockers as one exact revision.
            # The earlier read established that this task is worth considering;
            # this snapshot is the source lease for the actual activation plus
            # resolution publication, so a peer edit cannot be overlaid.
            captured = _ticket_bytes(ref)
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
            if not _owner_in_scope(ticket, owner_filter) or ticket.status != "blocked":
                _replace_result(
                    results,
                    _result(
                        ref,
                        "failed",
                        "ticket changed before dependency activation; retry",
                        _operator_name(cfg, ref, ticket),
                    ),
                )
                continue
            blockers = [
                blocker
                for blocker in parse_blockers_text(blocker_text)
                if not blocker.resolved
            ]
            resolutions = _finished_blocker_dependencies(blockers, known)
            if not resolutions:
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
                        _operator_name(cfg, ref, ticket),
                    ),
                )
                continue

            dependency = ", ".join(dict.fromkeys(resolutions.values()))
            answers = {
                blocker: (
                    "Coga megalaunch automatically resolved this blocker after "
                    f"dependency {finished} finished."
                )
                for blocker, finished in resolutions.items()
            }
            if any(blocker not in answers for blocker in blockers):
                failure = _publish_partial_dependency_resolution(
                    cfg, ref, ticket, source_bytes=captured, answers=answers
                )
                if failure is not None:
                    drained_slugs.add(ref.id_slug)
                    _replace_result(results, failure)
                else:
                    remaining = "; ".join(
                        blocker.reason for blocker in blockers if blocker not in answers
                    )
                    _replace_result(
                        results,
                        _result(
                            ref, "skipped-unresolved-blocker", remaining,
                            _operator_name(cfg, ref, ticket),
                        ),
                    )
                # A later launch may finish another dependency. Partial
                # progress does not consume the task's one drain launch.
                continue

            drained_slugs.add(ref.id_slug)

            # Validate the prospective activation before either local write.
            # The durable helper then publishes activation and these answers as
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
                source_bytes=captured,
                blocker_resolution=("system", answers),
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
                owner_filter=owner_filter,
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
            if result.stops_run:
                return results
            if result.launched:
                launched_in_pass = True
                break

        if not launched_in_pass:
            break
    return results


def _finished_blocker_dependencies(
    blockers: list[Blocker], known_refs: dict[str, TaskRef]
) -> dict[Blocker, str]:
    """Map each satisfied open blocker record to its exact finished task refs."""
    slugs = sorted(known_refs, key=lambda slug: (-len(slug), slug))
    finished: dict[str, bool] = {}
    resolutions: dict[Blocker, str] = {}
    for blocker in blockers:
        if blocker.resolved:
            continue
        named = [slug for slug in slugs if _reason_names_task(blocker.reason, slug)]
        for slug in named:
            if slug not in finished:
                try:
                    finished[slug] = read_ticket(known_refs[slug]).status == "done"
                except TicketNotFoundError:
                    finished[slug] = True
                except TicketError:
                    finished[slug] = False
        if named and all(finished[slug] for slug in named):
            resolutions[blocker] = ", ".join(named)
    return resolutions


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
    return replace(
        result,
        detail=f"dependency {dependency} finished; {result.detail}",
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
    each). Picks run whatever their owner: the owner flags only shaped the
    list the picker offered, never the confirmed set.

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
    # not-ready ticket to a launchable shape (workflow, contexts, agent).
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
                    _operator_name(cfg, ref, ticket),
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
            # Activation freezes the snapshot, seeds step 1, and selects a main
            # agent — all routing inputs. Classify that prospective state before
            # admitting the pick to the plan.
            # The source ticket's blockers were already classified above.
            candidate = _candidate_result(
                cfg, ref, prepared, explicit=True, blockers=[]
            )
            if candidate is not None:
                results.append(candidate)
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
                    _operator_name(cfg, ref, ticket),
                )
            )
            continue
        candidate = _candidate_result(cfg, ref, ticket, explicit=True)
        if candidate is not None:
            results.append(candidate)
            continue
        blocked_resume = ticket.status == "blocked"
        needs_activation = ticket.status in {"draft", "paused", "blocked"}
        activation_bytes: bytes | None = None
        if needs_activation:
            # Bind preparation, every launch preflight, and the eventual write
            # to one exact ticket revision. Reading the parsed ticket back from
            # the captured bytes closes the read/capture gap; the activation
            # compares those same bytes immediately before its write.
            captured = activation_bytes = _ticket_bytes(ref)
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
                        _operator_name(cfg, ref, ticket),
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
                        _operator_name(cfg, ref, ticket),
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
            activation_bytes=activation_bytes,
            explicit=True,
            owner_filter=None,
        )
        # A selected candidate can cross a current-step, routing, or terminal
        # gate at the exact reread just like a sweep candidate.  Only a real
        # attempt consumes the shared limit.
        if result.launched or not result.outcome.startswith("skipped-"):
            attempted += 1
        results.append(result)
        if result.stops_run:
            # Later picks stay untouched: none is reread or activated.
            break
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
    shape before phase 2 tries to activate it. Ordinary interview failures leave
    the draft for checking; a retained-state refusal exits 75 immediately so
    neither the queue nor its parent wrapper can refresh or sweep it.
    """
    try:
        bootstrap_ref = resolve_bootstrap(cfg, "ticket")
    except TaskNotFoundError:
        return
    bootstrap_ticket = read_ticket(bootstrap_ref)
    # Interviewer selection is the same chain `coga ticket` uses, minus its
    # picker: this batched pass never prompts. It picks who runs the interview
    # and never persists onto the edited ticket. A bad agent from any term is
    # reported, then the draft is left as it is and the run continues.
    try:
        launch_agent = resolve_authoring_agent(
            cfg,
            source_ticket=ticket,
            bootstrap_ticket=bootstrap_ticket,
            agent_override=agent_override,
        )
    except ConfigError as exc:
        typer.secho(
            f"{ref.id_slug}: skipping guided authoring: {exc}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return
    code = invoke_ticket_authoring(cfg, ref, agent_name=launch_agent)
    if code == git.RETRY_WITHOUT_SWEEP_EXIT_CODE:
        raise SystemExit(code)
    # Ordinary interview failures leave the draft for the check phase.


def launchable_candidates(
    cfg: Config,
    *,
    directory: str | None = None,
    owner: str | None = None,
    all_owners: bool = False,
) -> list[tuple[TaskRef, Ticket]]:
    """The tasks the interactive picker offers, ordered like `coga status`.

    Listed as the default status view reads (last updated, newest first, tasks
    with no recorded activity last; ties keep drain order), so the picker and
    the triage view are one list. Display order only: the engine re-derives
    the launch queue from `coga.service_order` and treats the confirmed set as
    a filter, so a numbered pipeline (`1-`, `2-`, `3-`) still runs in number
    order however its rows were displayed.

    Every non-terminal task whose `owner:` is in the owner filter — the
    operator's (`cfg.current_user`) by default, `owner`'s instead, or every
    owner's (owner-less tickets included) with `all_owners`; see
    `resolve_owner_filter`. Within that owner, `done` and `canceled` are the
    only exclusions. The picker deliberately does *not* pre-filter for
    launchability: a human-assigned ticket, a stepless one, or an ask-less
    `blocked` ticket all show up, because hiding them silently would let the
    operator pick "everything" and quietly miss real work. Checking a row that
    can't actually launch is not an error — the staged run reports it
    (`skipped-human-gate` / `skipped-unlaunchable`) instead of dropping it.
    Drafts are offered as-is; the prepare phase authors them into shape.
    Unreadable tickets are the only silent skip (the picker offers choices; the
    run reports failures).
    """
    owner_filter = resolve_owner_filter(cfg, owner=owner, all_owners=all_owners)
    candidates: list[tuple[TaskRef, Ticket]] = []
    for ref in filter_tasks_under(_tasks_in_service_order(cfg), directory, cfg):
        try:
            ticket = read_ticket(ref)
        except TicketError:
            continue
        if ticket.status in TERMINAL_STATUSES:
            continue
        if not _owner_in_scope(ticket, owner_filter):
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
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_selection(cfg: Config) -> list[str]:
    """Read the last confirmed selection; `MegalaunchError` when there is none."""
    path = _selection_path(cfg)
    if not path.is_file():
        raise MegalaunchError(
            "No saved selection to relaunch — confirm a picker run first "
            "(`coga megalaunch --pick`)."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
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
                    _operator_name(cfg, ref, ticket),
                )
        else:
            detail = (
                "; ".join(blocker.reason for blocker in blockers)
                or "status is blocked"
            )
            return _result(
                ref,
                "skipped-unresolved-blocker",
                detail,
                _operator_name(cfg, ref, ticket),
            )
    elif blockers and ticket.status in {"active", "in_progress"} and not explicit:
        # An `in_progress` resume goes through the same gates as an `active`
        # start — it must not dodge the blocker gate just because a prior
        # session already flipped the status.
        detail = "; ".join(blocker.reason for blocker in blockers)
        return _result(
            ref,
            "skipped-unresolved-blocker",
            detail,
            _operator_name(cfg, ref, ticket),
        )

    # A picked stepless ticket acquires its first step during activation. The
    # check phase and final preflight apply these gates to that prepared view;
    # an unactivated draft has no position to route from.
    if (
        explicit
        and ticket.status in {"draft", "paused", "blocked"}
        and not ticket.step
    ):
        return None

    # A draft has no current step yet — activation freezes the workflow and
    # seeds step 1, so its step gate runs post-activation in
    # `_launch_until_stop`. Everything else is gated here.
    if ticket.status == "draft":
        return None
    if ticket.current_step() is None:
        return _result(
            ref,
            "skipped-human-gate",
            "no current workflow step",
            _operator_name(cfg, ref, ticket),
        )

    # Megalaunch keeps its own human gate even under `--agent`: an ordinary
    # override selects the worker for agent-held steps, and never authorizes an
    # assist on a step the workflow hands to the owner.
    from coga.bump import OperatorResolutionError, resolve_operator

    try:
        operator = resolve_operator(
            cfg, ref, ticket, allow_prospective_default=True
        )
    except OperatorResolutionError as exc:
        return _result(ref, "failed", f"unresolvable operator: {exc}")
    if operator is None or operator.is_human:
        who = "no operator" if operator is None else operator.name
        return _result(
            ref,
            "skipped-human-gate",
            f"current step hands off to {who}",
            None if operator is None else operator.name,
        )
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
    activation_bytes: bytes | None = None,
    explicit: bool = False,
    owner_filter: str | None,
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
                _operator_name(cfg, ref, ticket),
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
                    _operator_name(cfg, ref, ticket),
                    launched=launched,
                )
            except (UnicodeDecodeError, TicketError, TaskFileError) as exc:
                return _result(
                    ref,
                    "failed",
                    f"unreadable ticket: {exc}",
                    _operator_name(cfg, ref, ticket),
                    launched=launched,
                )

            # The outer queue scan is only a candidate hint. A peer may change
            # owner, status, blockers, or the current workflow step before this
            # exact reread, so reapply every sweep gate to these same bytes
            # before deriving a prompt or lifecycle mutation from them.
            if not explicit and not _owner_in_scope(ticket, owner_filter):
                return _result(
                    ref,
                    "skipped-human-gate",
                    f"owner {ticket.owner or 'unassigned'} is outside the "
                    f"owner filter ({owner_filter})",
                    _operator_name(cfg, ref, ticket),
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
                    _operator_name(cfg, ref, ticket),
                    launched=launched,
                )
            if ticket.status in TERMINAL_STATUSES:
                return _result(
                    ref,
                    "skipped-unlaunchable",
                    f"status is {ticket.status}",
                    _operator_name(cfg, ref, ticket),
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

        # A deferred activation belongs to the first step only. Preflight the
        # prospective `active` view, materializing the exact `in_progress`
        # prompt, environment, and agent this launch will use. Commit the flip
        # only once every refusal below has passed, so a ticket whose session
        # never starts is never left claiming it did.
        # The exact bytes this step found before any lifecycle write: what a
        # failed agent start restores (a deferred pick's draft/paused/blocked
        # capture, otherwise the active or in_progress preflight read).
        pre_launch_bytes = activation_bytes if activate else preflight_source_bytes
        preflight_view = ticket
        prepared_activation: Ticket | None = None
        if activate:
            prepared = _prepare_for_launch(cfg, ref, ticket)
            if isinstance(prepared, MegalaunchResult):
                return prepared
            preflight_view = prepared
            prepared_activation = prepared
            candidate = _candidate_result(
                cfg, ref, prepared, explicit=True, blockers=[]
            )
            if candidate is not None:
                return candidate

        from coga.bump import OperatorResolutionError, resolve_operator

        try:
            operator = resolve_operator(cfg, ref, preflight_view)
        except OperatorResolutionError as exc:
            return _result(ref, "failed", str(exc), launched=launched)
        if operator is None or operator.is_human:
            who = "no operator" if operator is None else operator.name
            return _result(
                ref,
                "completed",
                f"handed off to {who}",
                None if operator is None else operator.name,
                launched=launched,
            )
        # Select from the same prepared ticket the preflight and activation
        # will use. An override applies only to the first launched step; every
        # later step follows the ticket's own derived routing, so `other-agent`
        # rotation still lands on the configured peer.
        launch_agent = (
            (agent_override or operator.name) if first_step else operator.name
        )
        first_step = False

        transaction = run_claimed_agent_session(
            cfg, ref,
            source_bytes=(activation_bytes if activate else preflight_source_bytes),
            prospective_ticket=preflight_view, agent_name=launch_agent,
            activation=prepared_activation if activate else None,
            idle_timeout=idle_timeout, max_session=max_session,
        )
        activate = False
        if transaction.activation_error is not None:
            return _activation_refusal(
                cfg, ref, preflight_view, ticket.status, transaction.activation_error
            )
        if transaction.refusal is not None:
            return _result(ref, "failed", transaction.refusal, launch_agent, launched=launched)
        before, session = transaction.before, transaction.session
        assert before is not None and session is not None

        launched = True
        if getattr(session, "exec_failed", False):
            return _restore_after_failed_start(
                cfg,
                ref,
                exit_code=session.exit_code,
                claimed_bytes=transaction.claimed_bytes,
                pre_launch_bytes=pre_launch_bytes,
                agent=launch_agent,
            )
        after = read_ticket(ref)
        # Advisory only, observed on the existing post-session read and before
        # any supervisor-owned reblock, so it can neither change the result
        # below nor mistake that reblock for the agent's change.
        warning = unsignalled_advance_warning(
            ref.id_slug,
            (before.status, before.step),
            (after.status, after.step),
            done_signalled=session.done_signalled,
        )
        if warning:
            typer.secho(warning, fg=typer.colors.YELLOW, err=True)
        if blocked_resume:
            # A resumed blocked launch may run to `in_progress` so the session
            # can discuss, `coga unblock`, and continue. If it exited with the
            # ask still open, return it to the blocked queue (visible to
            # `status --blocked` and blocker reminders) instead of chaining.
            blocked_resume = False
            reblocked = _reblock_unresolved(cfg, ref, after)
            if reblocked is not None:
                return reblocked
            after = read_ticket(ref)
        if after.status == "blocked":
            blockers = open_blockers(ref.ticket_path)
            detail = "; ".join(blocker.reason for blocker in blockers) or "blocked"
            return _result(
        ref, "blocked", detail, _operator_name(cfg, ref, after), launched=True
    )
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
                _operator_name(cfg, ref, after),
                launched=True,
            )
        if session.exit_code != 0:
            return _result(
                ref,
                "failed",
                f"agent exited with code {session.exit_code}",
                _operator_name(cfg, ref, after),
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
                _operator_name(cfg, ref, after),
                launched=True,
            )
        ticket = after


def _restore_after_failed_start(
    cfg: Config,
    ref: TaskRef,
    *,
    exit_code: int,
    claimed_bytes: bytes | None,
    pre_launch_bytes: bytes | None,
    agent: str | None,
) -> MegalaunchResult:
    """Put a failed-to-start ticket back exactly as this step found it.

    A compare-and-set against the claim the child ran under: the pre-launch
    bytes (a pick's draft/paused/blocked capture, or the active/in_progress
    preflight read) go back with any `launch_generation` claim dropped, the
    audit line records why, and publication expects control's copy to be that
    same claim. Nothing is blocked or asked: an agent that cannot start is an
    environment problem, not the ticket's. Whatever happens, the returned row
    stops the run; a restore that cannot complete says so.
    """
    head = f"agent failed to start (exited with code {exit_code}); run stopped"
    next_step = (
        "fix the agent environment, then rerun megalaunch "
        "(`coga megalaunch --relaunch` replays a pick)"
    )

    def stopped(detail: str) -> MegalaunchResult:
        return MegalaunchResult(
            slug=ref.id_slug,
            outcome="failed",
            detail=f"{head}; {detail}",
            agent=agent,
            launched=True,
            stops_run=True,
        )

    if claimed_bytes is None:
        return stopped("launch claim unavailable; ticket needs manual reconciliation")
    if pre_launch_bytes is None:
        return stopped(
            "no pre-launch snapshot to restore; ticket needs manual reconciliation"
        )
    try:
        source = Ticket.parse(pre_launch_bytes.decode("utf-8"))
    except (UnicodeDecodeError, TicketError) as exc:
        return stopped(
            f"pre-launch snapshot unreadable ({exc}); ticket needs manual "
            "reconciliation"
        )
    prior = source.status
    if source.launch_generation is None:
        restored = pre_launch_bytes
    else:
        source.frontmatter.pop("launch_generation", None)
        restored = source.render().encode("utf-8")

    try:
        with git.state_lock(cfg):
            if _ticket_bytes(ref) != claimed_bytes:
                return stopped(
                    "ticket changed since launch admission; ticket needs manual reconciliation"
                )
            log_before = _log_bytes(cfg)
            try:
                atomic_write_bytes(ref.ticket_path, restored)
                append_log(
                    cfg,
                    ref.id_slug,
                    "megalaunch",
                    f"restored (in_progress → {prior}) — agent failed to start "
                    f"(exit {exit_code}); megalaunch run stopped",
                )
                if cfg.git_enabled:
                    git.sync_task_state(
                        cfg,
                        ref.path,
                        message=f"Ticket: {ref.id_slug} — restored {prior}",
                        expect={ref.ticket_path: claimed_bytes},
                        strict=True,
                    )
            except git.UncertainPublishError as exc:
                return stopped(
                    f"restored to {prior} locally but publication is uncertain; "
                    f"ticket needs manual reconciliation — {exc}"
                )
            except (OSError, git.GitError) as exc:
                # Definitely not on control: keep local state equal to the claim
                # control still holds rather than a restore nobody accepted.
                try:
                    rolled_back = restore_owned_ticket(
                        cfg, ref, claimed_bytes, log_before=log_before,
                        expected_bytes=restored,
                    )
                    if not rolled_back and _ticket_bytes(ref) != claimed_bytes:
                        raise OSError("ticket changed during the failed restore")
                except OSError as rollback_exc:
                    return stopped(
                        f"restore failed ({exc}) and local rollback failed ({rollback_exc}); "
                        "ticket needs manual reconciliation"
                    )
                return stopped(
                    f"restore to {prior} failed ({exc}); ticket needs manual reconciliation"
                )
    except (OSError, git.GitError) as exc:
        return stopped(
            f"restore could not be confirmed ({exc}); ticket needs manual reconciliation"
        )
    return stopped(f"restored to {prior}; {next_step}")


def _activation_refusal(
    cfg: Config,
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
            _operator_name(cfg, ref, ticket),
        )
    if isinstance(exc, WorkflowError):
        return _result(
            ref,
            "skipped-unlaunchable",
            f"`workflow:` ref could not be frozen — {exc}",
            _operator_name(cfg, ref, ticket),
        )
    if isinstance(exc, RequiredExtensionMissing):
        names = ", ".join(repr(f) for f in exc.fields)
        return _result(
            ref,
            "skipped-unlaunchable",
            f"required extension field(s) empty: {names}",
            _operator_name(cfg, ref, ticket),
        )
    if isinstance(exc, BlackboardNeedsSynthesis):
        return _result(
            ref,
            "skipped-unlaunchable",
            f"blackboard needs synthesis before first launch: {exc.reason}",
            _operator_name(cfg, ref, ticket),
        )
    if isinstance(exc, MainAgentUnavailable):
        return _result(
            ref,
            "skipped-unlaunchable",
            f"main agent unavailable: {exc}",
            _operator_name(cfg, ref, ticket),
        )
    return _result(ref, "failed", str(exc), _operator_name(cfg, ref, ticket))


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
        return _activation_refusal(cfg, ref, ticket, prior, exc)
    return prospective


def _publish_partial_dependency_resolution(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    source_bytes: bytes,
    answers: dict[Blocker, str],
) -> MegalaunchResult | None:
    """Publish satisfied asks against exact bytes, retaining `blocked`.

    Match activation's recovery: restore a definitely refused write, retain
    an uncertain one as evidence, and never overwrite a changed local ticket.
    """
    with git.state_lock(cfg):
        log_before = _log_bytes(cfg)
        written: bytes | None = None
        try:
            written = update_blackboard_under_barrier(
                cfg, ref.ticket_path,
                lambda region: resolve_blockers_text(region, "system", answers),
                expected_bytes=source_bytes,
            )
            append_log(
                cfg, ref.id_slug, "megalaunch",
                "resolved finished dependency blockers (still blocked)",
            )
            git.sync_task_state(
                cfg, ref.path,
                message=f"Ticket: {ref.id_slug} — dependency asks resolved",
                expect={ref.ticket_path: source_bytes},
                strict=True,
            )
        except git.UncertainPublishError as exc:
            return _result(
                ref, "failed",
                "dependency resolution publication outcome is uncertain; "
                f"local state retained for reconciliation — {exc}",
                _operator_name(cfg, ref, ticket),
            )
        except (OSError, UnicodeError, TaskFileError, git.GitError) as exc:
            if written is not None:
                try:
                    unchanged = _ticket_bytes(ref) == written
                except OSError:
                    unchanged = False
                if not unchanged:
                    return _result(
                        ref, "failed",
                        "dependency resolution publication failed and the local "
                        "ticket changed or could not be read; "
                        f"local state retained for reconciliation — {exc}",
                        _operator_name(cfg, ref, ticket),
                    )
                restore_owned_ticket(cfg, ref, source_bytes, log_before=log_before, expected_bytes=written)
            return _result(
                ref, "failed", f"could not publish dependency resolutions: {exc}",
                _operator_name(cfg, ref, ticket),
            )
    return None


def _reblock_unresolved(cfg: Config, ref: TaskRef, after: Ticket) -> MegalaunchResult | None:
    result = reblock_unresolved_resume(
        cfg, ref, slack_actor=cfg.current_user,
        log_message="blocked: unresolved blocker still open after resumed megalaunch pick exited",
        echo_owner_text="owner {owner} needs to answer",
    )
    if result.kind in {"noop", "already_blocked"}:
        return None
    return _result(
        ref, "failed" if result.kind == "invalid" else "blocked",
        result.detail, _operator_name(cfg, ref, after), launched=True,
    )


def _chain_stop_result(
    cfg: Config, ref: TaskRef, after: Ticket
) -> MegalaunchResult | None:
    """Terminal chain state after an agent step, or None to keep chaining."""
    if after.status == "blocked":
        blockers = open_blockers(ref.ticket_path)
        detail = "; ".join(blocker.reason for blocker in blockers) or "blocked"
        return _result(
        ref, "blocked", detail, _operator_name(cfg, ref, after), launched=True
    )
    if after.status == "canceled":
        return _result(
            ref,
            "canceled",
            "task canceled",
            _operator_name(cfg, ref, after),
            launched=True,
        )
    if after.status in TERMINAL_STATUSES:
        return _result(
            ref,
            "completed",
            f"task {after.status}",
            _operator_name(cfg, ref, after),
            launched=True,
        )
    if after.status != "in_progress":
        return _result(
            ref,
            "completed",
            f"status is {after.status}",
            _operator_name(cfg, ref, after),
            launched=True,
        )
    from coga.bump import OperatorResolutionError, resolve_operator

    try:
        operator = resolve_operator(cfg, ref, after)
    except OperatorResolutionError as exc:
        return _result(ref, "failed", str(exc), launched=True)
    if operator is None or operator.is_human:
        who = "no operator" if operator is None else operator.name
        return _result(
            ref,
            "completed",
            f"handed off to {who}",
            None if operator is None else operator.name,
            launched=True,
        )
    return None


def _operator_name(cfg: Config, ref: TaskRef, ticket: Ticket) -> str | None:
    """The derived operator's nickname for a report row, or None if unknown.

    Report rows are a record of what the sweep decided, so a ticket whose
    routing cannot resolve must still produce a row. Eligibility decisions call
    `resolve_operator` directly and refuse loudly instead.
    """
    from coga.bump import OperatorResolutionError, resolve_operator

    try:
        operator = resolve_operator(
            cfg, ref, ticket, allow_prospective_default=True
        )
    except OperatorResolutionError:
        return None
    return operator.name if operator is not None else None


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
    if run.owner_scope is not None:
        lines.extend(["", f"Owner: {run.owner_scope}"])
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


def _activate_for_launch(
    cfg: Config, ref: TaskRef, ticket: Ticket, *,
    log_message: str | None = None, prepared: Ticket | None = None,
    source_bytes: bytes | None = None,
    blocker_resolution: tuple[str, dict[Blocker, str]] | None = None,
) -> MegalaunchResult | None:
    prior = ticket.status
    failure = activate_claimed_ticket(
        cfg, ref, ticket, log_message=log_message, prepared=prepared,
        source_bytes=source_bytes, blocker_resolution=blocker_resolution,
    )
    if failure is None:
        return None
    return _activation_refusal(cfg, ref, ticket, prior, failure.error)


def megalaunch(
    directory: str | None = typer.Argument(
        None,
        metavar="[DIR]",
        help=(
            "Only sweep (or pick from) tasks under `tasks/<DIR>/` (a "
            "directory path, nested ones included, e.g. `marketing` or "
            "`marketing/social`), same as `coga status <DIR>`. Omit to "
            "cover every task."
        ),
    ),
    pick: bool = typer.Option(
        False,
        "--pick",
        help=(
            "Choose interactively: an arrow-key list of your non-terminal "
            "tasks (any status except done/canceled; see --owner and "
            "--all-owners), "
            "nothing pre-checked; the confirmed set is prepared (a batch "
            "prompt offers to run the authoring interview on picked drafts), "
            "checked, then launched — each pick is activated as its own launch "
            "starts — and is saved for --relaunch."
            " Selection filters the service-ordered queue; the order tasks "
            "are picked does not set their run order."
        ),
    ),
    relaunch: bool = typer.Option(
        False,
        "--relaunch",
        help="Re-run the last confirmed picker selection.",
    ),
    owner: str | None = typer.Option(
        None,
        "--owner",
        metavar="NAME",
        help=(
            "Cover NAME's tickets (their `owner:` field) instead of yours, on "
            "both --pick and the sweep. The sweep applies the same "
            "launchability gates and dependency drain it applies to yours."
        ),
    ),
    all_owners: bool = typer.Option(
        False,
        "--all-owners",
        help=(
            "Cover every owner's tickets, owner-less ones included, on both "
            "--pick and the sweep. Cannot be combined with --owner."
        ),
    ),
    max_tasks: int | None = typer.Option(
        None,
        "--max-tasks",
        min=1,
        help=(
            "Stop after this many launch attempts; dependency-drain retries "
            "count against the same budget."
        ),
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help=(
            "Use this configured agent type for picked-draft authoring and "
            "the first launched step (ephemeral; human-assigned working "
            "steps still skip, unlike an explicit `coga launch --agent` "
            "assist)."
        ),
    ),
) -> None:
    """Drain launchable tasks sequentially.

    Tasks drain oldest-first by their first `coga/log.md` entry. Naming tasks
    in a sub-directory with numeric prefixes such as `1-`, `2-`, `3-`
    sequences that directory as one contiguous block in number order; this is
    a naming convention, not a flag.
    """
    if os.environ.get("COGA_SCRIPT_HELP") == "1":
        raise typer.Exit(2)
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    if agent is not None:
        try:
            cfg.agent_type(agent)
        except ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            sys.exit(2)

    # Pick and queue from control's state, not a stale local copy: every
    # later read (picker list, sweep queue, saved selection) sees these files.
    # A feature/detached checkout only fetches; Git-off, non-Git and no-remote
    # repos skip. `False` means control could not be brought level, and
    # refresh already said why on stderr.
    if not git.refresh(cfg):
        typer.secho(
            "megalaunch: could not bring this checkout level with control; "
            "nothing was picked or launched.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(1)
    try:
        cfg = load_config(cfg.repo_root)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        selection = _resolve_selection(
            cfg,
            directory,
            pick=pick,
            relaunch=relaunch,
            owner=owner,
            all_owners=all_owners,
        )
    except (MegalaunchError, UnknownDirectoryError, ConfigError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    if selection is not None and not selection:
        # The picker (or an empty candidate list) already said why.
        return

    # A picked selection that includes drafts gets one batch question: run the
    # guided authoring interview on them first, or launch what's ready and let
    # the not-ready drafts report themselves. Only asked when there's a draft
    # to author, so a pick of ready work is never interrupted.
    author_drafts = _confirm_author_drafts(cfg, selection) if selection else False

    try:
        run = run_megalaunch(
            cfg,
            max_tasks=max_tasks,
            agent_override=agent,
            directory=directory,
            selection=selection,
            author_drafts=author_drafts,
            # A pick already applied the owner filter to the list it offered;
            # the confirmed selection runs as the human checked it.
            owner=owner if selection is None else None,
            all_owners=all_owners if selection is None else False,
        )
    except (MegalaunchError, UnknownDirectoryError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    # Local outcome to stdout before the notification post, so a Slack crash
    # still leaves the run summary visible (coga/sync convention).
    if owner is not None and selection is None and not run.results:
        # Owners are free strings with no registry to validate against, so an
        # unmatched name is an empty sweep, said plainly rather than an error.
        typer.echo(f"No launchable tasks owned by {owner}.")
    typer.echo(render_run_summary(run))
    message = _drain_post_text(run)
    if message is not None:
        notification.post(cfg, message)
    if run.counts["failed"]:
        sys.exit(1)


def _confirm_author_drafts(cfg: Config, selection: list[str]) -> bool:
    """Ask once whether to author the picked drafts, or `False` if none.

    A picked `draft` is not-yet-ready work: authoring it (the guided
    `coga ticket` interview) is what makes it launchable. But forcing an
    interview on every pick is heavy, so this is a single opt-in prompt raised
    only when the confirmed selection actually contains a draft — a pick of
    ready work is never interrupted.
    """
    wanted = set(selection)
    drafts = [
        ref.id_slug
        for ref in list_tasks(cfg)
        if ref.id_slug in wanted and _is_draft(ref)
    ]
    if not drafts:
        return False
    noun = "draft" if len(drafts) == 1 else "drafts"
    return typer.confirm(
        f"{len(drafts)} picked {noun} ({', '.join(sorted(drafts))}) — run the "
        "guided authoring interview to make them ready before launching?",
        default=True,
    )


def _is_draft(ref: TaskRef) -> bool:
    try:
        return read_ticket(ref).status == "draft"
    except TicketError:
        return False


def _resolve_selection(
    cfg: Config,
    directory: str | None,
    *,
    pick: bool,
    relaunch: bool,
    owner: str | None = None,
    all_owners: bool = False,
) -> list[str] | None:
    """Turn the flags into the engine's `selection`.

    `None` means the non-explicit sweep; an empty list means the human
    confirmed nothing (caller reports and exits cleanly).
    """
    if owner is not None and all_owners:
        raise MegalaunchError("--owner and --all-owners cannot be combined.")
    if relaunch and (pick or directory is not None):
        raise MegalaunchError(
            "--relaunch replays the last saved selection; combining it with "
            "--pick or a directory is ambiguous."
        )
    if relaunch and (owner is not None or all_owners):
        raise MegalaunchError(
            "--relaunch replays the last saved selection as-is; combining it "
            "with --owner or --all-owners is ambiguous."
        )

    if relaunch:
        return _saved_selection_still_on_disk(cfg)
    if not pick:
        # Default: the non-interactive sweep of launchable active tasks.
        return None

    # --pick: the interactive arrow-key picker over an explicit list.
    if not interactive_stdio_has_tty():
        raise MegalaunchError(
            "The megalaunch picker is interactive and requires a TTY. "
            "Drop --pick for the non-interactive sweep."
        )
    candidates = launchable_candidates(
        cfg, directory=directory, owner=owner, all_owners=all_owners
    )
    if not candidates:
        if all_owners:
            typer.echo("No tasks to pick (only done/canceled tasks exist).")
        else:
            typer.echo(
                f"No tasks to pick: no non-terminal tasks owned by "
                f"{owner if owner is not None else cfg.current_user}"
                " (--all-owners lists every owner's)."
            )
        return []
    selection = _pick_selection(candidates)
    if selection:
        save_selection(cfg, selection)
        typer.echo(f"Picked: {', '.join(selection)}")
    else:
        typer.echo("Nothing selected — nothing launched.")
    return selection


def _saved_selection_still_on_disk(cfg: Config) -> list[str]:
    """The saved selection minus tasks that no longer exist, reported loudly."""
    saved = load_selection(cfg)
    existing = {ref.id_slug for ref in list_tasks(cfg)}
    kept = [slug for slug in saved if slug in existing]
    for slug in saved:
        if slug not in existing:
            typer.secho(
                f"Saved selection: {slug} no longer exists — skipped.",
                fg=typer.colors.YELLOW,
                err=True,
            )
    if not kept:
        raise MegalaunchError(
            "None of the saved selection's tasks exist anymore — run the "
            "picker again."
        )
    return kept


def _decode_key(data: bytes) -> str:
    """Map a raw keypress byte sequence to a picker action ('' = ignore)."""
    if data in (b"\x1b[A", b"\x1bOA", b"k"):
        return "up"
    if data in (b"\x1b[B", b"\x1bOB", b"j"):
        return "down"
    if data == b" ":
        return "space"
    if data in (b"\r", b"\n"):
        return "enter"
    if data in (b"q", b"\x1b", b"\x03"):  # q, bare Esc, Ctrl-C
        return "quit"
    if data == b"a":
        return "all"
    if data == b"n":
        return "none"
    return ""


def _read_key(resize_fd: int) -> str:
    """Read one keypress from the terminal in raw mode, decoded to an action.

    `resize_fd` is the read end of the picker's SIGWINCH self-pipe (see
    `_pick_selection`); a byte there wins over a keypress and comes back as
    the synthetic "resize" action. Returning — rather than redrawing here —
    matters: the `finally` restores cooked mode first, so the caller never
    renders while raw mode (no OPOST) would staircase the output.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        # TCSADRAIN, not setraw's default TCSAFLUSH: a keypress that lands
        # between reads (e.g. racing a resize redraw) must survive re-entry,
        # not be flushed with the queue.
        tty.setraw(fd, termios.TCSADRAIN)
        ready = select.select([fd, resize_fd], [], [])[0]
        if resize_fd in ready:
            # Drain so a flurry of resizes coalesces into one redraw.
            os.read(resize_fd, 1024)
            return "resize"
        data = os.read(fd, 1)
        if data == b"\x1b":
            # Arrow keys arrive as ESC [ A / ESC O A; a bare Esc sends nothing
            # more, so a short poll distinguishes the two.
            while len(data) < 3 and select.select([fd], [], [], 0.02)[0]:
                data += os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return _decode_key(data)


# Windows console extended keys arrive from `getwch` as a "\xe0" (or
# "\x00") prefix and a scan character; map them to the POSIX byte forms so
# `_decode_key` stays the one decoder.
_WINDOWS_EXTENDED_KEYS = {"H": b"\x1b[A", "P": b"\x1b[B"}
_WINDOWS_KEY_POLL = 0.05


def _windows_console() -> bool:
    return os.name == "nt"


class _PosixKeys:
    """Raw-mode key reads plus the SIGWINCH self-pipe (see `_read_key`)."""

    def __enter__(self) -> _PosixKeys:
        # SIGWINCH self-pipe: `_read_key` blocks in os.read/select, and PEP
        # 475 retries reads around signals, so a flag set by a handler would
        # never be seen while the read stays blocked. The wakeup fd turns the
        # signal into a readable byte `_read_key` can select on. The no-op
        # handler is required — SIGWINCH is ignored by default, and only
        # signals with a Python-level handler reach the wakeup fd. Installed
        # for the whole picker so a resize landing between keypresses (cooked
        # mode) is buffered, not lost.
        self._resize_read, self._resize_write = os.pipe()
        os.set_blocking(self._resize_write, False)
        self._previous_wakeup = signal.set_wakeup_fd(self._resize_write)
        self._previous_handler = signal.signal(
            signal.SIGWINCH, lambda signum, frame: None
        )
        return self

    def __exit__(self, *exc: object) -> None:
        signal.signal(signal.SIGWINCH, self._previous_handler)
        signal.set_wakeup_fd(self._previous_wakeup)
        os.close(self._resize_read)
        os.close(self._resize_write)

    def read(self) -> str:
        return _read_key(self._resize_read)

    def cancelled(self) -> bool:
        # Raw mode turns Ctrl+C into the "\x03" key on POSIX.
        return False


class _WindowsKeys:
    """`msvcrt` polling for the Windows console, with a whole-picker quit flag.

    With processed console input, Ctrl+C can arrive as a SIGINT between reads
    (during the poll sleep or a redraw) rather than as the "\x03" key. The
    handler only sets a flag; the picker treats it exactly like `q`, and it
    wins over a queued Enter. There is no SIGWINCH, so a changed terminal size
    is polled and returned as "resize".
    """

    def __enter__(self) -> _WindowsKeys:
        from coga.repl_supervisor_nt import ConsoleModes

        self._quit = False
        self._modes = ConsoleModes.save()
        self._size = shutil.get_terminal_size()
        self._previous_handler = signal.signal(signal.SIGINT, self._on_interrupt)
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            signal.signal(signal.SIGINT, self._previous_handler)
        finally:
            self._modes.restore()

    def _on_interrupt(self, signum, frame) -> None:  # type: ignore[no-untyped-def]
        self._quit = True

    def cancelled(self) -> bool:
        return self._quit

    def read(self) -> str:
        import msvcrt

        while True:
            if self._quit:
                return "quit"
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char in ("\x00", "\xe0"):
                    data = _WINDOWS_EXTENDED_KEYS.get(msvcrt.getwch(), b"")
                else:
                    data = char.encode("utf-8", "replace")
                action = _decode_key(data)
                return "quit" if self._quit else action
            size = shutil.get_terminal_size()
            if size != self._size:
                self._size = size
                return "resize"
            time.sleep(_WINDOWS_KEY_POLL)


def _pick_selection(candidates: list[tuple[TaskRef, Ticket]]) -> list[str]:
    """Arrow-key picker: ↑/↓ (or j/k) move, Space toggles, Enter launches.

    Nothing starts checked — the list reaches wide (drafts, paused, blocked,
    and other owners' tickets under --owner/--all-owners), so every launch is an explicit opt-in. Returns
    the confirmed slugs, or an empty list when the human backed out (`q`/Esc,
    Ctrl+C, or confirming with nothing checked).
    """
    console = Console()
    cursor = 0
    selected: set[int] = set()
    keys = _WindowsKeys() if _windows_console() else _PosixKeys()
    with keys:
        with Live(
            _picker_view(candidates, selected, cursor, console),
            console=console,
            auto_refresh=False,
            transient=True,
        ) as live:
            while True:
                key = keys.read()
                if key == "quit" or keys.cancelled():
                    return []
                if key == "enter":
                    return [candidates[i][0].id_slug for i in sorted(selected)]
                if key == "up":
                    cursor = (cursor - 1) % len(candidates)
                elif key == "down":
                    cursor = (cursor + 1) % len(candidates)
                elif key == "space":
                    selected ^= {cursor}
                elif key == "all":
                    selected = set(range(len(candidates)))
                elif key == "none":
                    selected = set()
                # "resize" needs no branch: falling through re-renders, and
                # _picker_view reads console.size fresh on every render.
                live.update(
                    _picker_view(candidates, selected, cursor, console), refresh=True
                )
                if keys.cancelled():
                    return []


def _picker_window(total: int, cursor: int, rows: int) -> tuple[int, int]:
    """Half-open [start, end) of candidate indices to show for this cursor.

    Rich's Live defaults to vertical_overflow="ellipsis", which keeps the
    *first* screenful of a taller-than-terminal render (LiveRender renders
    `lines[: height - 1]` plus an ellipsis line). So without windowing the
    bottom of a long list is never drawn and the cursor vanishes on the way
    down. We scroll the viewport to keep the cursor inside it, leaving a
    one-row margin at each edge when there is more list to reveal.

    This only holds if each candidate costs exactly one terminal line —
    `_picker_view` is responsible for that, by truncating rather than wrapping.
    """
    if rows <= 0 or total <= rows:
        return 0, total
    # Anchor the window on the "page" the cursor falls in, then nudge so the
    # cursor is never pinned to the very top/bottom edge while more rows exist.
    start = max(0, min(cursor - rows // 2, total - rows))
    return start, start + rows


def _picker_view(
    candidates: list[tuple[TaskRef, Ticket]],
    selected: set[int],
    cursor: int,
    console: Console,
) -> Group:
    # Chrome is an unconditional 5 lines: 2 for the table (header row + header
    # rule), 1 for the hint, and 2 for the scroll indicators — which are always
    # rendered, blank when there is nothing above/below, so the reserve holds at
    # the list ends too and the frame doesn't jitter by a row as you scroll past
    # them.
    rows = max(1, console.size.height - 5)
    start, end = _picker_window(len(candidates), cursor, rows)

    # `_picker_window` budgets in candidates, so every row must cost exactly one
    # terminal line. `no_wrap`/`ellipsis` on every column is what buys that —
    # a wrapped row costs more than its one budgeted line and overflows.
    #
    # The ratios matter as much as the truncation. Left to itself, an
    # all-no_wrap table measures wider than the terminal (slugs and titles run
    # long), Rich falls through to its last-resort even reduction, and *every*
    # column shrinks — the marker and checkbox collapse to nothing. Declaring
    # the elastic columns flexible (`ratio` + `expand`) hands Rich the
    # slack it needs from them alone, so the fixed narrow columns survive down
    # to ~50 cells.
    table = Table(show_lines=False, show_edge=False, pad_edge=False, expand=True)
    table.add_column("", width=1, no_wrap=True, overflow="ellipsis")
    table.add_column("sel", width=3, no_wrap=True, overflow="ellipsis")
    table.add_column("slug", ratio=2, no_wrap=True, overflow="ellipsis")
    table.add_column("status", no_wrap=True, overflow="ellipsis")
    table.add_column("owner", ratio=1, no_wrap=True, overflow="ellipsis")
    table.add_column("step", ratio=1, no_wrap=True, overflow="ellipsis")
    table.add_column("title", ratio=3, no_wrap=True, overflow="ellipsis")
    for index in range(start, end):
        ref, ticket = candidates[index]
        table.add_row(
            Text("❯" if index == cursor else " "),
            # Text, not str: a bare "[x]" would be eaten as Rich markup.
            Text("[x]" if index in selected else "[ ]"),
            ref.id_slug,
            ticket.status,
            ticket.owner or "-",
            ticket.step or "-",
            ticket.title,
            style="reverse" if index == cursor else None,
        )
    # These sit outside the table and wrap on their own, so they need the same
    # truncation the columns got — the hint line alone is 64 cells wide.
    def _line(text: str) -> Text:
        return Text(text, style="dim", no_wrap=True, overflow="ellipsis")

    return Group(
        _line(f"  ↑ {start} more above" if start > 0 else ""),
        table,
        _line(
            f"  ↓ {len(candidates) - end} more below"
            if end < len(candidates)
            else ""
        ),
        _line("↑/↓ move · Space toggle · a all · n none · Enter launch · q quit"),
    )


def _drain_post_text(run: MegalaunchRun) -> str | None:
    """One live line: what was drained.

    Silent when the run had no results at all — an empty repo is lifecycle
    noise, not an outcome a teammate needs within minutes.
    """
    if not run.results:
        return None
    counts = run.counts
    launched = [result.slug for result in run.results if result.launched]
    parts = [
        "launched " + ", ".join(f"*{slug}*" for slug in launched)
        if launched
        else "nothing launched"
    ]
    not_launchable = (
        counts["skipped-unresolved-blocker"]
        + counts["skipped-human-gate"]
        + counts["skipped-unlaunchable"]
    )
    if not_launchable:
        parts.append(f"{not_launchable} not launchable")
    if counts["drained"]:
        parts.append(f"{counts['drained']} dependency-drained")
    if counts["failed"]:
        parts.append(f"{counts['failed']} failed")
    scope = [run.directory] if run.directory is not None else []
    if run.owner_scope is not None:
        scope.append(f"owner {run.owner_scope}")
    if run.agent_override is not None:
        scope.append(f"as {run.agent_override}")
    if run.selection is not None:
        scope.append("selected")
    label = f"Megalaunch drain ({', '.join(scope)})" if scope else "Megalaunch drain"
    return label + ": " + "; ".join(parts)


def main(argv: list[str]) -> int:
    app = typer.Typer(add_completion=False)
    app.command()(megalaunch)
    try:
        app(args=argv, prog_name="coga megalaunch")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
