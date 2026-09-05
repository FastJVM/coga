"""`coga mark <state> <slug>` — change a ticket's status.

Four subcommands: `mark active`, `mark paused`, `mark done`, and `mark
canceled`. Each verb is
the literal `status` value it sets, so the command shape mirrors the
frontmatter field.

`coga launch` owns the `active` → `in_progress` start transition. On a
workflow's final step, `coga bump` delegates to the same shared `mark_done`
finalizer used here.
"""

from __future__ import annotations

import sys

import typer

from coga import git, pr_assist
from coga.config import Config, ConfigError, load_config
from coga.lifecycle import CANCELABLE_STATUSES
from coga.logfile import log_path
from coga.mark import (
    BlackboardNeedsSynthesis,
    CancellationError,
    RequiredExtensionMissing,
    StrandedProductCode,
    WorkflowMissing,
)
from coga.mark import format_blackboard_synthesis_refusal
from coga.mark import mark_active as _mark_active
from coga.mark import mark_canceled as _mark_canceled
from coga.mark import mark_done as _mark_done
from coga.mark import mark_paused as _mark_paused
from coga.repl_supervisor import emit_done_marker
from coga.notification import digest_spool_target_path, preflight_post
from coga.period_state import parent_ticket_path, read_snapshot
from coga.tasks import TaskNotFoundError, TaskRef, read_ticket, resolve_task
from coga.ticket import Ticket
from coga.validate import TaskValidationError
from coga.workflow import WorkflowError

app = typer.Typer(
    name="mark",
    help="Change a ticket's status (active / paused / done / canceled).",
    no_args_is_help=True,
    add_completion=False,
)


_ACTIVE_FROM = {"draft", "paused"}
_PAUSED_FROM = {"active", "in_progress"}
_DONE_FROM = {"active", "in_progress"}
_CANCELED_FROM = set(CANCELABLE_STATUSES)


@app.command("active")
def active(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
) -> None:
    """Set status to `active`. Allowed from `draft` or `paused`."""
    cfg, ref, ticket = _load(task)
    _require_message_nonempty(message)
    _check_transition(ref.id_slug, ticket.status, _ACTIVE_FROM, "active")

    suffix = f" — {message}" if message else ""
    actor = f"human:{cfg.current_user}"
    log_message = f"activated ({ticket.status} → active){suffix}"

    try:
        _mark_active(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
            echo=f"{ref.id_slug}: active",
        )
    except WorkflowMissing:
        _bail(
            f"Cannot activate {ref.id_slug}: ticket has no workflow. A "
            "workflow-less ticket has no steps and can't be advanced via "
            "`coga bump`. Set `workflow: <name>` in `ticket.md` (see "
            f"coga/workflows/) or run `coga ticket {ref.id_slug}` to "
            "fill it in, then retry."
        )
    except WorkflowError as exc:
        _bail(
            f"Cannot activate {ref.id_slug}: its `workflow:` ref could not "
            f"be frozen — {exc}"
        )
    except RequiredExtensionMissing as exc:
        names = ", ".join(repr(f) for f in exc.fields)
        _bail(
            f"Cannot activate {ref.id_slug}: required extension field(s) "
            f"empty: {names}. Fill them in `ticket.md` then retry."
        )
    except BlackboardNeedsSynthesis as exc:
        _bail(
            format_blackboard_synthesis_refusal(
                ref.id_slug, action="activate", reason=exc.reason
            )
        )
    except TaskValidationError as exc:
        _bail(str(exc))


@app.command("paused")
def paused(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
) -> None:
    """Set status to `paused`. Allowed from `active` or `in_progress`."""
    cfg, ref, ticket = _load(task)
    ticket, rollback = _capture_assist_transition(
        cfg,
        ref,
        include_spool=False,
        include_period_parent=False,
    )
    _require_message_nonempty(message)
    _check_transition(ref.id_slug, ticket.status, _PAUSED_FROM, "paused")
    assist = _acquire_assist_transition(cfg, ref, rollback)

    suffix = f" — {message}" if message else ""
    actor = (
        f"agent:{assist.agent}"
        if assist is not None
        else f"human:{cfg.current_user}"
    )
    log_message = f"paused ({ticket.status} → paused){suffix}"
    publication_succeeded = False

    def record_publication() -> None:
        nonlocal publication_succeeded
        publication_succeeded = True

    try:
        _mark_paused(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
            echo=f"{ref.id_slug}: paused",
            feature_publication=(assist.lease if assist is not None else None),
            feature_publication_guard=(
                assist.guard if assist is not None else None
            ),
            mutation_snapshot=rollback,
            after_sync=record_publication if rollback is not None else None,
        )
    except git.FeaturePublicationError as exc:
        _bail_strict_transition(
            cfg,
            ref,
            "paused",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )
    except TaskValidationError as exc:
        if rollback is not None:
            _bail_strict_transition(
                cfg,
                ref,
                "paused",
                exc,
                rollback,
                publication_succeeded=publication_succeeded,
            )
        _bail(str(exc))
    except BaseException as exc:
        if rollback is None:
            raise
        _bail_strict_transition(
            cfg,
            ref,
            "paused",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )


@app.command("done")
def done(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Finish even if a direct/body ticket committed product code that "
        "won't reach the control branch (the code will stay stranded).",
    ),
) -> None:
    """Set status to `done`. Allowed from `active` or `in_progress`."""
    cfg, ref, ticket = _load(task)
    ticket, rollback = _capture_assist_transition(
        cfg,
        ref,
        include_spool=True,
        include_period_parent=True,
    )
    _require_message_nonempty(message)
    _check_transition(ref.id_slug, ticket.status, _DONE_FROM, "done")
    _preflight_assist_outcome(cfg, ref, rollback)
    assist = _acquire_assist_transition(cfg, ref, rollback)

    suffix = f" — {message}" if message else ""
    finisher = (
        assist.agent
        if assist is not None
        else ticket.assignee or cfg.current_user
    )
    actor = (
        f"agent:{assist.agent}"
        if assist is not None
        else f"human:{cfg.current_user}"
    )
    log_message = f"task done{suffix}"
    # A workflow-less ticket has no current step, so collapse the transition.
    prev = ticket.current_step()
    transition = f": {prev['name']} → done" if prev else ""
    slack_text = (
        f"🎉 {finisher} finished *{ref.id_slug}* "
        f"\"{ticket.title}\"{transition}{suffix}"
    )
    publication_succeeded = False

    def record_publication() -> None:
        nonlocal publication_succeeded
        publication_succeeded = True

    try:
        _mark_done(
            cfg, ref, ticket,
            actor=actor,
            log_message=log_message,
            slack_text=slack_text,
            digest_detail=f"{finisher} finished{transition or ' → done'} ✅{suffix}",
            image_url=cfg.gif_for("done"),
            echo=f"{ref.id_slug}: done",
            force=force,
            feature_publication=(assist.lease if assist is not None else None),
            feature_publication_guard=(
                assist.guard if assist is not None else None
            ),
            mutation_snapshot=rollback,
            after_sync=record_publication if rollback is not None else None,
        )
    except git.FeaturePublicationError as exc:
        _bail_strict_transition(
            cfg,
            ref,
            "done",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )
    except StrandedProductCode as exc:
        if rollback is not None:
            _bail_strict_transition(
                cfg,
                ref,
                "done",
                exc,
                rollback,
                publication_succeeded=publication_succeeded,
            )
        listed = "\n".join(f"    {p}" for p in exc.paths)
        _bail(
            f"Cannot finish {ref.id_slug}: its {exc.workflow_name} workflow has "
            f"no push/PR step, but this checkout committed tracked product code "
            f"that is not on {cfg.git_control_branch!r}:\n"
            f"{listed}\n"
            f"That code will strand off the control branch if this checkout "
            f"or its branch is removed. Move the ticket to a code/* workflow "
            f"(code/with-self-review or code/with-review) so it opens a PR, or "
            f"re-run with --force to finish anyway and keep the code stranded."
        )
    except TaskValidationError as exc:
        if rollback is not None:
            _bail_strict_transition(
                cfg,
                ref,
                "done",
                exc,
                rollback,
                publication_succeeded=publication_succeeded,
            )
        _bail(str(exc))
    except BaseException as exc:
        if rollback is None:
            raise
        _bail_strict_transition(
            cfg,
            ref,
            "done",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )

    # `mark done` is a session-end transition; tell a supervising
    # `coga launch` to tear down the agent's REPL. Other `mark`
    # transitions (active / paused) are not terminal and intentionally
    # skip the marker. The task's `id_slug` scopes the signal to this
    # ticket (see `emit_done_marker`) — worktree-independent, unlike a
    # resolved path, so it matches whichever checkout the command runs in.
    emit_done_marker(session_id=ref.id_slug)


@app.command("canceled")
def canceled(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str = typer.Option(
        ...,
        "--message",
        help="Required reason for cancellation; persisted in the audit log.",
    ),
) -> None:
    """Set status to `canceled`. Allowed from every non-terminal status."""
    cfg, ref, ticket = _load(task)
    ticket, rollback = _capture_assist_transition(
        cfg,
        ref,
        include_spool=True,
        include_period_parent=False,
    )
    reason = message.strip()
    if not reason:
        _bail("--message cannot be empty")
    _check_transition(ref.id_slug, ticket.status, _CANCELED_FROM, "canceled")
    _preflight_assist_outcome(cfg, ref, rollback)
    assist = _acquire_assist_transition(cfg, ref, rollback)

    canceler = assist.agent if assist is not None else cfg.current_user
    publication_succeeded = False

    def record_publication() -> None:
        nonlocal publication_succeeded
        publication_succeeded = True

    try:
        _mark_canceled(
            cfg,
            ref,
            ticket,
            actor=(
                f"agent:{canceler}"
                if assist is not None
                else f"human:{canceler}"
            ),
            reason=reason,
            slack_text=(
                f"🚫 {canceler} canceled *{ref.id_slug}* "
                f'"{ticket.title}": {reason}'
            ),
            digest_detail=f"{canceler} canceled — {reason}",
            image_url=cfg.gif_for("canceled"),
            echo=f"{ref.id_slug}: canceled — {reason}",
            feature_publication=(assist.lease if assist is not None else None),
            feature_publication_guard=(
                assist.guard if assist is not None else None
            ),
            mutation_snapshot=rollback,
            after_sync=record_publication if rollback is not None else None,
        )
    except git.FeaturePublicationError as exc:
        _bail_strict_transition(
            cfg,
            ref,
            "canceled",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )
    except (CancellationError, TaskValidationError) as exc:
        if rollback is not None:
            _bail_strict_transition(
                cfg,
                ref,
                "canceled",
                exc,
                rollback,
                publication_succeeded=publication_succeeded,
            )
        _bail(str(exc))
    except BaseException as exc:
        if rollback is None:
            raise
        _bail_strict_transition(
            cfg,
            ref,
            "canceled",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )

    # Cancellation is terminal and can happen from inside a launched agent
    # session. Release the same supervisor sentinel as `mark done` / `block`.
    emit_done_marker(session_id=ref.id_slug)


# --- helpers -----------------------------------------------------------------


def _load(task: str):
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    ticket = read_ticket(ref)
    return cfg, ref, ticket


def _capture_assist_transition(
    cfg: Config,
    ref: TaskRef,
    *,
    include_spool: bool,
    include_period_parent: bool,
) -> tuple[Ticket, git.FileMutationRollback | None]:
    """Pin exact lifecycle inputs before a possible inherited assist lease."""
    if not pr_assist.assist_publication_requested(ref):
        return read_ticket(ref), None

    paths = [log_path(cfg)]
    union_paths = [log_path(cfg)]
    if include_spool:
        spool_path = digest_spool_target_path(cfg)
        if spool_path is not None:
            paths.append(spool_path)
            union_paths.append(spool_path)
    if include_period_parent:
        snapshot = read_snapshot(ref.path)
        if snapshot is not None:
            parent_ticket = parent_ticket_path(cfg, snapshot)
            if parent_ticket.parent.is_dir():
                paths.append(parent_ticket)
    rollback = git.capture_task_mutation_snapshot(
        ref.path,
        extra_paths=paths,
        union_paths=union_paths,
    )
    ticket_bytes = rollback.originals[ref.ticket_path]
    if ticket_bytes is None:
        _bail(
            f"Task {ref.id_slug} has no ticket.md.",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    return Ticket.parse(ticket_bytes.decode("utf-8")), rollback


def _acquire_assist_transition(
    cfg: Config,
    ref: TaskRef,
    rollback: git.FileMutationRollback | None,
) -> pr_assist.AssistPublication | None:
    if rollback is None:
        return None
    try:
        assist = pr_assist.assist_publication_from_env(
            cfg,
            ref,
            mutation_snapshot=rollback,
        )
    except git.FeaturePublicationError as exc:
        _bail(
            f"Could not verify the recorded assist branch before changing "
            f"{ref.id_slug}: {exc}",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    if assist is None:
        _bail(
            f"Could not rebuild {ref.id_slug}'s recorded assist capability.",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    return assist


def _preflight_assist_outcome(
    cfg: Config,
    ref: TaskRef,
    rollback: git.FileMutationRollback | None,
) -> None:
    """Validate a strict live outcome channel before any publication lease."""
    if rollback is None or digest_spool_target_path(cfg) is not None:
        return
    try:
        preflight_post(cfg)
    except typer.Exit:
        _bail(
            f"Could not complete {ref.id_slug} from the recorded assist: "
            "notification configuration must be valid before strict state "
            "publication.",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )


def _bail_strict_transition(
    cfg: Config,
    ref: TaskRef,
    transition: str,
    exc: BaseException,
    rollback: git.FileMutationRollback | None,
    *,
    publication_succeeded: bool,
) -> None:
    rollback_note = ""
    if publication_succeeded or isinstance(exc, git.UncertainFeaturePublicationError):
        rollback_note = (
            "; generated state was retained because publication succeeded "
            "or could not be determined"
        )
    elif rollback is not None and rollback.generated is not None:
        refused = git.restore_files_under_barrier(cfg, rollback)
        if refused:
            names = ", ".join(str(path) for path in refused)
            rollback_note = (
                "; concurrent edits were retained instead of being "
                f"overwritten at {names}"
            )
    detail = str(exc).strip() or type(exc).__name__
    _bail(
        f"Could not complete {ref.id_slug}'s strict {transition} transition "
        f"after {type(exc).__name__}: {detail}{rollback_note}",
        exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
    )


def _require_message_nonempty(message: str | None) -> None:
    if message is not None and not message.strip():
        _bail("--message cannot be empty")


def _check_transition(
    id_slug: str, current: str, allowed_from: set[str], target: str
) -> None:
    if current == target:
        _bail(f"Task {id_slug} is already {target!r}.")
    if current not in allowed_from:
        allowed = " or ".join(repr(s) for s in sorted(allowed_from))
        _bail(
            f"Task {id_slug} is {current!r}; mark {target} requires {allowed}."
        )


def _bail(msg: str, *, exit_code: int = 2) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(exit_code)
