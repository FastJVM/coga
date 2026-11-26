"""Status transitions — the shared core of `coga mark` and lifecycle callers.

These finalizers mutate ticket frontmatter, append a repo-global `log.md`
line (tagged by task ref), and echo
the local outcome. Terminal outcomes post live to Slack as they happen;
routine active/paused transitions are intentionally local-only noise. The CLI
commands and the auto-merge scanner all reuse the same helpers so the on-disk
shape stays identical regardless of who triggered the transition.

`advance_step` lives in `coga.bump` — that's the workflow plane.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Literal
from pathlib import Path

import typer

from coga.blackboard import prelaunch_blackboard_synthesis_reason_text
from coga.bump import OperatorResolutionError, resolve_main_agent, resolve_operator
from coga.config import Config
from coga.lifecycle import CANCELABLE_STATUSES
from coga.logfile import append_log
from coga.paths import log_path, load_workflow
from coga.period_state import (
    StateSnapshot,
    parent_ticket_path,
    read_snapshot,
    stale_keys,
)
from coga.notification import notify, post
from coga.taskfile import TaskFileError, split_body
from coga.tasks import TaskRef, TargetRef
from coga.ticket import Ticket, TicketError
from coga.validate import TaskValidationError, assert_task_valid
from coga.workflow import WorkflowError
from coga.paths import RepoResourceUnreadable

# Workflows with no push/PR step: finishing one with committed product code
# strands that code off the control branch. Kept as a set so the guard can grow
# to other bodyless flows without touching the call site.
_NO_PR_WORKFLOWS = {"direct/body"}


def mark_done(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    image_url: str | None = None,
    echo: str | None = None,
    force: bool = False,
    strict: bool = False,
) -> None:
    """Flip a ticket to `done`: write frontmatter, log, notify.

    `done` is the routine outcome Slack still needs, so it routes through
    `notification.notify`, which posts `slack_text` live (image and all).

    `echo` is the stdout line printed before the notify (so the local outcome
    is visible even if a live post crashes). Pass `None` to suppress — used by
    quiet auto-bump paths such as launch-time freshness checks.

    """
    owner = ticket.owner or cfg.current_user
    # Validate the prospective close before committing it, the way
    # `mark canceled` already does. An `other-agent` step that cannot resolve
    # against this machine's `[agents.*]` is a config fact rather than
    # something this write caused, so validating afterwards would leave a
    # ticket marked done on disk with no audit entry and no sync — on the very
    # tickets an operator is only trying to close.
    prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    prospective.frontmatter["status"] = "done"
    prospective.frontmatter.pop("step", None)
    assert_task_valid(cfg, ref, action="mark done", ticket_override=prospective)
    ticket.frontmatter = prospective.frontmatter
    ticket.write(ref.ticket_path)
    append_log(cfg, ref.id_slug, actor, log_message)
    snapshot = read_snapshot(ref.path)
    if echo is not None:
        typer.echo(echo)
    notify(
        cfg, slack_text, kind="done", owner=owner, task_path=ref.path,
        image_url=image_url, fatal=False,
    )
    _warn_if_state_not_advanced(cfg, ref, ticket, owner, snapshot)


class CancellationError(RuntimeError):
    """A requested transition would violate cancellation semantics."""


def mark_canceled(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    reason: str,
    slack_text: str,
    image_url: str | None = None,
    echo: str | None = None,
) -> None:
    """Flip any non-terminal ticket to ``canceled`` and record why.

    The reason is required in this shared layer, not only by Typer, so an
    internal caller cannot create an illegible cancellation. Cancellation
    clears ``step:`` like completion but deliberately leaves the body and
    blackboard untouched; an unresolved blocker therefore remains historical
    context while the ticket itself becomes terminal.
    """
    reason = reason.strip()
    if not reason:
        raise CancellationError("cancellation reason cannot be empty")
    if ticket.status not in CANCELABLE_STATUSES:
        raise CancellationError(
            f"status {ticket.status!r} cannot transition to 'canceled'"
        )

    prior_status = ticket.status
    owner = ticket.owner or cfg.current_user
    prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    prospective.frontmatter["status"] = "canceled"
    prospective.frontmatter.pop("step", None)
    assert_task_valid(
        cfg,
        ref,
        action="mark canceled",
        ticket_override=prospective,
    )
    ticket.frontmatter = prospective.frontmatter
    ticket.write(ref.ticket_path)
    append_log(
        cfg,
        ref.id_slug,
        actor,
        f"canceled ({prior_status} → canceled): {reason}",
    )
    if echo is not None:
        typer.echo(echo)
    notify(
        cfg,
        slack_text,
        kind="canceled",
        owner=owner,
        task_path=ref.path,
        image_url=image_url,
        fatal=False,
    )


def _warn_if_state_not_advanced(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    owner: str,
    snapshot: StateSnapshot | None,
) -> None:
    """Flag a period task that completed without advancing its declared state.

    A recurring task can declare the blackboard keys it owns (`state_keys:`);
    the creator snapshots their values into the period task. If a declared
    key still equals that snapshot when the run finishes, the run did the work
    but never recorded its high-water mark — the next firing will redo the same
    range. Warn locally and broadcast an important alert.

    No-op for any task without a snapshot — i.e. every non-recurring task. This
    is advisory only: it runs after the transition has already committed, and a
    failed broadcast must never turn a successful `mark done` into an error.
    """
    if snapshot is None:
        return
    stale = stale_keys(cfg, snapshot)
    if not stale:
        return

    keys = ", ".join(stale)
    typer.echo(
        f"⚠ declared state key(s) {keys} did not advance this run. The parent "
        f"recurring task's blackboard still holds the value this period started "
        f"with, so the next firing will redo the same range. Record state before "
        f"finishing (or record an explicit skip)."
    )

    try:
        post(
            cfg,
            f"⚠ {ref.id_slug} finished without advancing declared state "
            f"({keys}) — next run may duplicate work.",
            task_path=ref.path,
            owner=owner,
            important=True,
        )
    except Exception as exc:  # advisory broadcast — never break completion
        sys.stderr.write(f"[period-state] FYI broadcast failed: {exc}\n")


class RequiredExtensionMissing(RuntimeError):
    """Raised when `mark active` is called on a ticket with required-but-empty
    extension fields. The caller renders a per-field error message for the
    user.
    """

    def __init__(self, fields: list[str]):
        self.fields = fields
        super().__init__(
            f"ticket missing values for required extension fields: {fields}"
        )


class WorkflowMissing(RuntimeError):
    """Raised when `mark active` is called on a ticket with no workflow.

    A workflow-less ticket has no steps and can never be advanced by
    `coga bump`, so activating one would strand it. The workflow may be a
    bare string ref (frozen on the first `coga bump`) or an already-frozen
    dict — only `null`/missing is refused.
    """


class MainAgentUnavailable(RuntimeError):
    """Raised when activation cannot settle this ticket's main agent.

    Either the ticket names an agent that configuration no longer declares, or
    it names none and no `[agents.*]` table exists to default to. Both are
    routing inputs a human fixes; activation refuses rather than substituting a
    different agent behind the operator's back.
    """


class BlackboardNeedsSynthesis(RuntimeError):
    """Raised when a draft blackboard still carries pre-launch authoring notes."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def format_blackboard_synthesis_refusal(
    id_slug: str, *, action: str, reason: str
) -> str:
    """Render the operator-facing first-launch blackboard refusal."""
    return (
        f"Cannot {action} {id_slug}: the blackboard has pre-launch notes "
        f"({reason}). Merge the important parts into `## Description` / "
        "`## Context` before launch. If this blackboard content is "
        "intentionally part of the run, keep the durable launch notes under "
        "`## Production notes`, then retry."
    )


def _has_workflow(ticket: Ticket) -> bool:
    """True when the ticket carries a workflow `mark active` can accept.

    Accepts both a bare string ref (hand-authored, frozen here on activate)
    and an already-frozen workflow dict. Rejects `null`, missing, and empty
    values.
    """
    wf = ticket.workflow
    if isinstance(wf, str):
        return bool(wf.strip())
    if isinstance(wf, dict):
        return bool(wf)
    return False


def _freeze_workflow_ref(cfg: Config, ticket: Ticket) -> None:
    """Freeze a bare-string `workflow:` ref and ensure the ticket has a step.

    Hand-authored / guided-authored draft tickets carry `workflow:` as a
    plain workflow name. Activation is when that becomes real: we freeze the
    snapshot. We also seed `step: 1` whenever the ticket has no current step,
    so a fresh draft is launch-ready — `coga launch` composes the current
    step's skill from the frozen workflow. It is a no-op for the workflow dict
    of an `active`/`paused` ticket that already carries a step.

    Seeding a step writes no assignment: who holds step 1 is derived from the
    frozen role every time it is read (`coga.bump.resolve_operator`), so a
    stored nickname can no longer disagree with the snapshot's own role the way
    it once could. Raises `WorkflowError` if a string ref names no known
    workflow — every activation caller already renders that.

    Precondition: `_has_workflow(ticket)` is true, so `ticket.workflow` is a
    non-empty string or dict by the time we read its steps.
    """
    wf = ticket.workflow
    if isinstance(wf, str):
        wf_def = load_workflow(cfg, wf)
        ticket.frontmatter["workflow"] = wf_def.freeze()
    if not ticket.step:
        frozen = ticket.workflow or {}
        steps = frozen.get("steps") or []
        if steps:
            ticket.frontmatter["step"] = f"1 ({steps[0]['name']})"


def _select_main_agent(cfg: Config, ticket: Ticket) -> None:
    """Freeze this ticket's main agent, if it has not chosen one already.

    Activation is the moment approved work first needs an agent, so it is where
    an omitted choice becomes a concrete, stable identity: the configured
    default is resolved once and persisted in `agent:`. Everything afterwards —
    pause/resume, peer review, unblock, terminal transitions — retains it, so
    changing the default (the `default_agent` key, or `[agents.*]` order when
    it is unset) between launches changes only *future* activations
    and can never turn a ticket's `main -> peer -> main` rotation into
    `main -> peer -> peer`.

    An explicit choice is never replaced, only validated. Removing a selected
    agent from configuration is an error to fix, not permission to substitute
    another one. Peers stay live configuration and are deliberately not frozen
    here.
    """
    try:
        ticket.frontmatter["agent"] = resolve_main_agent(
            cfg, ticket.agent, allow_prospective_default=True
        )
    except OperatorResolutionError as exc:
        raise MainAgentUnavailable(str(exc)) from exc


def _assert_operator_resolves(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Refuse activation whose prepared step has no derivable operator.

    Activation is the last cheap boundary before a ticket becomes launchable, so
    a role token this machine cannot resolve — an ambiguous `other-agent`, an
    `owner` step on a ticket with no owner — fails here rather than surfacing
    later as a launch refusing a step its own snapshot declares. It runs on the
    prospective ticket, so a refusal leaves the stored bytes untouched.
    """
    try:
        resolve_operator(cfg, ref, ticket)
    except OperatorResolutionError as exc:
        raise WorkflowError(str(exc)) from exc


def _missing_required_extensions(cfg: Config, ticket: Ticket) -> list[str]:
    """Return names of `required = true` extension fields that are absent or
    empty on this ticket."""
    missing: list[str] = []
    for name, spec in cfg.ticket_fields.items():
        if not spec.required:
            continue
        value = ticket.frontmatter.get(name, "")
        if not isinstance(value, str) or not value.strip():
            missing.append(name)
    return missing


def _refuse_unsynthesized_draft_blackboard(
    cfg: Config, ticket: Ticket, prior_status: str | None
) -> None:
    """Refuse the first launch boundary when authoring notes remain.

    Reads the blackboard of the ticket being activated — the copy reconciled
    with fresh control — never the possibly stale on-disk file.
    """
    if prior_status != "draft":
        return
    _above, region = split_body(ticket.body, blackboard_required=False)
    if region is None:
        return
    reason = prelaunch_blackboard_synthesis_reason_text(region, cfg=cfg)
    if reason is not None:
        raise BlackboardNeedsSynthesis(reason)


def prepare_active(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
) -> None:
    """Validate and mutate ``ticket`` to active without writing durable state.

    Launch uses this pure preparation boundary to compose a prospective prompt
    before an assist's final publication gate. ``mark_active`` remains the
    durable wrapper that writes, audits, and optionally syncs the result.

    Main-agent selection lives here rather than in `mark_active` so it is part
    of the *prospective* preparation and commits only with the successful
    transition. A preparation that fails afterwards — a missing required
    extension, a refused publication — leaves the ticket's bytes untouched, so
    a newly chosen agent is never written to a real ticket by a failed attempt.
    """
    prior_status = ticket.status
    if prior_status == "canceled":
        raise CancellationError("a canceled ticket cannot be reactivated")
    _refuse_unsynthesized_draft_blackboard(cfg, ticket, prior_status)

    if not _has_workflow(ticket):
        raise WorkflowMissing()
    _freeze_workflow_ref(cfg, ticket)
    _select_main_agent(cfg, ticket)
    _assert_operator_resolves(cfg, ref, ticket)

    missing = _missing_required_extensions(cfg, ticket)
    if missing:
        raise RequiredExtensionMissing(missing)

    ticket.frontmatter["status"] = "active"
    # An active task has no live megalaunch claim. The next megalaunch writes
    # a fresh generation atomically with its `in_progress` transition.


def mark_active(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    echo: str | None = None,
    sync_state: bool = True,
    strict: bool = False,
) -> None:
    """Validate, activate, and audit the local ticket."""
    prepare_active(cfg, ref, ticket)
    assert_task_valid(cfg, ref, action="mark active", ticket_override=ticket)
    ticket.write(ref.ticket_path)
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)


def mark_in_progress(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    echo: str | None = None,
    strict: bool = False,
) -> None:
    """Set the local ticket in progress and audit the transition."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "in_progress"
    assert_task_valid(cfg, ref, action="mark in_progress", ticket_override=ticket)
    ticket.write(ref.ticket_path)
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        post(cfg, slack_text, task_path=ref.path, owner=owner, fatal=False)


def mark_blocked(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    image_url: str | None = None,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `blocked` without changing its workflow step."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "blocked"
    assert_task_valid(cfg, ref, action="mark blocked", ticket_override=ticket)
    ticket.write(ref.ticket_path)
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(
        cfg,
        slack_text,
        task_path=ref.path,
        owner=owner,
        image_url=image_url,
        # `coga block` ends the session: a Slack outage must not keep the
        # blocked ticket's agent REPL alive to its idle timeout.
        fatal=False,
    )


def mark_paused(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    echo: str | None = None,
    strict: bool = False,
) -> None:
    """Flip a ticket to `paused`: write frontmatter and log.

    Most pauses are silent on Slack (a human `mark paused`, the sweep parking
    a recurring run that returned unfinished): they pass no `slack_text` and
    nothing is broadcast. The one broadcasting caller is the recurring liveness watchdog,
    which pauses a wedged run and needs the team to see it — a recurring run
    that timed out is a `recurring-error`, so when `slack_text` is given the
    pause routes through `notification.notify`, posted live to important.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "paused"
    assert_task_valid(cfg, ref, action="mark paused", ticket_override=ticket)
    ticket.write(ref.ticket_path)
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        notify(
            cfg,
            slack_text,
            kind="recurring-error",
            owner=owner,
            task_path=ref.path,
            important=True,
            fatal=False,
        )


__all__ = [
    "mark_active",
    "prepare_active",
    "PREPARE_ACTIVE_ERRORS",
    "mark_in_progress",
    "mark_blocked",
    "mark_paused",
    "mark_done",
    "mark_canceled",
    "CancellationError",
    "RequiredExtensionMissing",
    "WorkflowMissing",
    "MainAgentUnavailable",
]


PREPARE_ACTIVE_ERRORS = (
    WorkflowMissing,
    WorkflowError,
    RequiredExtensionMissing,
    BlackboardNeedsSynthesis,
    MainAgentUnavailable,
    RepoResourceUnreadable,
)
