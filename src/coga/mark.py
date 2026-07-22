"""Status transitions — the shared core of `coga mark` and lifecycle callers.

These finalizers mutate ticket frontmatter, append a repo-global `log.md`
line (tagged by task ref), and echo
the local outcome. Terminal outcomes still enter Slack through the digest path;
routine active/paused transitions are intentionally local-only noise. The CLI
commands and the auto-merge scanner all reuse the same helpers so the on-disk
shape stays identical regardless of who triggered the transition.

`advance_step` lives in `coga.bump` — that's the workflow plane.
"""

from __future__ import annotations

from collections.abc import Callable

import typer

from coga import git
from coga.blackboard import prelaunch_blackboard_synthesis_reason
from coga.config import Config
from coga.lifecycle import CANCELABLE_STATUSES
from coga.logfile import append_log
from coga.paths import recurring_dir, resolve_workflow_path
from coga.period_state import StateSnapshot, read_snapshot, stale_keys
from coga.notification import digest_spool_path, notify, post
from coga.tasks import TaskRef
from coga.ticket import Ticket
from coga.validate import assert_task_valid
from coga.workflow import Workflow

# Workflows with no push/PR step: finishing one with committed product code
# strands that code off the control branch. Kept as a set so the guard can grow
# to other bodyless flows without touching the call site.
_NO_PR_WORKFLOWS = {"direct/body"}


class StrandedProductCode(RuntimeError):
    """Raised when a `direct/body` ticket is finished with committed product
    code that will not reach the control branch (the workflow has no push/PR
    step). The CLI renders the offending paths and points at a `code/*`
    workflow; `--force` overrides.
    """

    def __init__(self, workflow_name: str, paths: list[str]):
        self.workflow_name = workflow_name
        self.paths = paths
        super().__init__(
            f"{workflow_name} task committed {len(paths)} tracked product "
            "file(s) not on the control branch"
        )


def _workflow_name(ticket: Ticket) -> str | None:
    """The ticket's workflow name, whether frozen (dict) or a bare-string ref."""
    wf = ticket.workflow
    if isinstance(wf, dict):
        name = wf.get("name")
        return str(name) if name else None
    if isinstance(wf, str):
        return wf.strip() or None
    return None


def _assert_no_stranded_product_code(cfg: Config, ref: TaskRef, ticket: Ticket) -> None:
    """Refuse to finish a no-PR-workflow ticket that committed product code.

    A `direct/body` (or other push/PR-less) workflow lands only Coga OS state on
    the control branch; any tracked product code the agent committed rides a
    throwaway branch or detached checkout that never reaches `main` and dangles
    when that checkout is removed. Detect it before the `done` write and raise
    so the CLI can steer the ticket to a `code/*` workflow (or `--force` past
    it).
    """
    name = _workflow_name(ticket)
    if name not in _NO_PR_WORKFLOWS:
        return
    stranded = git.stranded_product_paths(cfg, ref.path)
    if stranded:
        raise StrandedProductCode(name or "direct/body", stranded)


def _state_guard(cfg: Config, ref: TaskRef) -> Callable[[str], None]:
    """The regression guard every transition below hands to its git sync.

    A transition's sync overlays this ticket wholesale onto the control tip, so
    a checkout holding a stale copy — one that went stale while an agent worked,
    or while the `autoclose-merged` sweep closed the ticket from the primary
    checkout — would otherwise bury the newer state. The guard re-checks the
    control copy on every landing attempt, including the base refetched after a
    non-fast-forward retry, and refuses rather than overwriting terminal or
    further-advanced state.

    The refusal is loud but non-fatal, and deliberately lands *after* the local
    ticket write: the transition the human asked for stays on disk, git declines
    to publish it, and the checkout is left visibly behind control (`coga
    status` flags it via `stale_coga_task_rels`). Moving the write behind a
    fetch would put the network on every status transition.
    """
    return git.ticket_state_guard(cfg, ref.ticket_path)


def mark_done(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str,
    digest_detail: str,
    image_url: str | None = None,
    echo: str | None = None,
    force: bool = False,
) -> None:
    """Flip a ticket to `done`: write frontmatter, log, notify.

    `done` is the routine outcome Slack still needs, so it routes through
    `notification.notify`: spooled into the daily digest when that ticket is
    installed, else posted live as `slack_text` (image and all).
    `digest_detail` is the one-liner shown under this ticket in the digest.

    `echo` is the stdout line printed before the notify (so the local outcome
    is visible even if a live post crashes). Pass `None` to suppress — used by
    quiet auto-bump paths such as launch-time freshness checks.

    A `direct/body` ticket that committed tracked product code off the control
    branch is refused with `StrandedProductCode` (the code would strand); pass
    `force=True` to override. See `_assert_no_stranded_product_code`.
    """
    if not force:
        _assert_no_stranded_product_code(cfg, ref, ticket)
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark done")
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    notify(
        cfg,
        slack_text,
        kind="done",
        detail=digest_detail,
        ticket=ref.id_slug,
        owner=owner,
        watchers=ticket.watchers,
        task_path=ref.path,
        image_url=image_url,
    )
    snapshot = read_snapshot(ref.path)
    _sync_done_state(cfg, ref, snapshot)
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
    digest_detail: str,
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
        detail=digest_detail,
        ticket=ref.id_slug,
        owner=owner,
        watchers=ticket.watchers,
        task_path=ref.path,
        image_url=image_url,
    )
    paths = [ref.path]
    spool_path = digest_spool_path(cfg)
    if spool_path is not None:
        paths.append(spool_path)
    git.sync_paths(
        cfg,
        ref.path,
        paths,
        message=f"Ticket: {ref.id_slug} — canceled",
        land_union_files_to_control=True,
        guard=_state_guard(cfg, ref),
    )


def _sync_done_state(
    cfg: Config, ref: TaskRef, snapshot: StateSnapshot | None
) -> None:
    message = f"Ticket: {ref.id_slug} — done"
    guard = _state_guard(cfg, ref)
    if snapshot is None:
        git.sync_task_state(cfg, ref.path, message=message, guard=guard)
        return

    paths = [ref.path]
    # The parent template's working state (high-water / state keys) lives in the
    # blackboard region of its single-file ticket.md, so sync that file.
    parent_ticket = recurring_dir(cfg) / snapshot.parent / "ticket.md"
    if parent_ticket.parent.is_dir():
        paths.append(parent_ticket)
    git.sync_paths(cfg, ref.path, paths, message=message, guard=guard)


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
    range. Warn locally and broadcast an FYI.

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
            watchers=ticket.watchers,
        )
    except Exception as exc:  # advisory broadcast — never break completion
        import sys

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
    of an `active`/`paused` ticket that already carries a step. Raises
    `WorkflowError` if a string ref names no known workflow.

    Precondition: `_has_workflow(ticket)` is true, so `ticket.workflow` is a
    non-empty string or dict by the time we read its steps.
    """
    wf = ticket.workflow
    if isinstance(wf, str):
        wf_def = Workflow.load(resolve_workflow_path(cfg, wf))
        ticket.frontmatter["workflow"] = wf_def.freeze()
    if not ticket.step:
        steps = (ticket.workflow or {}).get("steps") or []
        if steps:
            ticket.frontmatter["step"] = f"1 ({steps[0]['name']})"


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
    ref: TaskRef, prior_status: str | None
) -> None:
    """Refuse the first launch boundary when authoring notes remain."""
    if prior_status != "draft":
        return
    reason = prelaunch_blackboard_synthesis_reason(
        ref.ticket_path,
        blackboard_required=False,
    )
    if reason is not None:
        raise BlackboardNeedsSynthesis(reason)


def mark_active(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `active`: write frontmatter and log.

    Refuses to activate a workflow-less ticket. A bare-string `workflow:`
    ref is frozen into its snapshot here so the activated ticket is
    launch-ready. Also refuses if any `required = true` extension field is
    empty. Activation is intentionally silent in Slack; the task log and git
    sync remain the audit trail.
    """
    prior_status = ticket.status
    if prior_status == "canceled":
        raise CancellationError("a canceled ticket cannot be reactivated")
    _refuse_unsynthesized_draft_blackboard(ref, prior_status)

    if not _has_workflow(ticket):
        raise WorkflowMissing()
    _freeze_workflow_ref(cfg, ticket)

    missing = _missing_required_extensions(cfg, ticket)
    if missing:
        raise RequiredExtensionMissing(missing)

    ticket.frontmatter["status"] = "active"
    ticket.write(ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark active")
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    git.sync_task_state(
        cfg,
        ref.path,
        message=f"Ticket: {ref.id_slug} — active",
        guard=_state_guard(cfg, ref),
    )


def mark_in_progress(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `in_progress`: write frontmatter, log, optionally post."""
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark in_progress")
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        post(cfg, slack_text, task_path=ref.path, owner=owner, watchers=ticket.watchers)
    git.sync_task_state(
        cfg,
        ref.path,
        message=f"Ticket: {ref.id_slug} — in_progress",
        guard=_state_guard(cfg, ref),
    )


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
    ticket.write(ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark blocked")
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    post(
        cfg,
        slack_text,
        task_path=ref.path,
        owner=owner,
        watchers=ticket.watchers,
        image_url=image_url,
    )
    git.sync_task_state(
        cfg,
        ref.path,
        message=f"Ticket: {ref.id_slug} — blocked",
        guard=_state_guard(cfg, ref),
    )


def mark_paused(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    actor: str,
    log_message: str,
    slack_text: str | None = None,
    digest_detail: str | None = None,
    echo: str | None = None,
) -> None:
    """Flip a ticket to `paused`: write frontmatter and log.

    Most pauses are silent on Slack (a human `mark paused`, the interactive
    recurring-cleanup path): they pass neither `slack_text` nor `digest_detail`
    and nothing is broadcast. The one broadcasting caller is the recurring
    liveness watchdog, which pauses a wedged run and needs the team to see it —
    a recurring run that timed out is a `recurring-error`, so when `slack_text`
    is given the pause routes through `notification.notify` (digest-spooled when the
    ticket is installed, else posted live); `digest_detail` is its one-liner.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["status"] = "paused"
    ticket.write(ref.ticket_path)
    assert_task_valid(cfg, ref, action="mark paused")
    append_log(cfg, ref.id_slug, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    if slack_text is not None:
        notify(
            cfg,
            slack_text,
            kind="recurring-error",
            detail=digest_detail or slack_text,
            ticket=ref.id_slug,
            owner=owner,
            watchers=ticket.watchers,
            task_path=ref.path,
        )
    git.sync_task_state(
        cfg,
        ref.path,
        message=f"Ticket: {ref.id_slug} — paused",
        guard=_state_guard(cfg, ref),
    )


__all__ = [
    "mark_active",
    "mark_in_progress",
    "mark_blocked",
    "mark_paused",
    "mark_done",
    "mark_canceled",
    "CancellationError",
    "RequiredExtensionMissing",
    "WorkflowMissing",
    "StrandedProductCode",
]
