"""`coga bump` — move through a workflow."""

from __future__ import annotations

import os
import sys

import typer

from coga import git, pr_assist
from coga.bump import (
    AssigneeResolutionError,
    advance_step,
    resolve_step_assignee,
    rewind_status_error,
)
from coga.config import ConfigError, load_config
from coga.logfile import log_path
from coga.mark import StrandedProductCode, mark_done
from coga.notification import digest_spool_target_path, preflight_post
from coga.paths import resolve_workflow_path
from coga.period_state import parent_ticket_path, read_snapshot
from coga.step_gate import gate_publishes_current_branch, gate_unmet_reason
from coga.taskfile import read_blackboard
from coga.repl_supervisor import (
    EXPECTED_STEP_ENV,
    EXPECTED_TASK_ENV,
    emit_done_marker,
)
from coga.tasks import (
    TaskRef,
    TaskNotFoundError,
    resolve_task,
)
from coga.ticket import Ticket
from coga.validate import TaskValidationError, assert_task_valid
from coga.workflow import Workflow, WorkflowError


def bump(
    task: str = typer.Argument(..., help="Task ID or id-slug."),
    message: str | None = typer.Option(
        None,
        "--message",
        help="Optional FYI to piggy-back on the state-transition broadcast.",
    ),
    to_step: int | None = typer.Option(
        None,
        "--to",
        help="Human-only: rewind to an earlier 1-based workflow step number.",
    ),
    backward: bool = typer.Option(
        False,
        "--backward",
        help="Human-only: rewind one workflow step.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="When finishing the final step, allow committed direct/body "
        "product code to remain stranded off the control branch.",
    ),
) -> None:
    """Finish the current step, or let a human rewind to an earlier step.

    A forward bump advances to the next workflow step, or marks the ticket
    done when the current step is final. Tickets without a workflow can't be
    bumped at all.
    """
    if message is not None and not message.strip():
        _bail("--message cannot be empty")
    if to_step is not None and backward:
        _bail("Use either --to or --backward, not both.")

    rewind = to_step is not None or backward
    if rewind and os.environ.get("COGA_SUPERVISED"):
        _bail(
            "Agents cannot rewind from a supervised coga launch. "
            "Call `coga block --task <id> --reason \"...\"`; a human can "
            "rewind with `coga bump <id> --to <step>`."
        )

    suffix = f" — {message}" if message else ""

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    assist_requested = pr_assist.assist_publication_requested(ref)
    if rewind and assist_requested:
        _bail(
            "Agents cannot rewind from a recorded assist. Call `coga block "
            "--task <id> --reason \"...\"`; a human can rewind outside the "
            "assist with `coga bump <id> --to <step>`."
        )
    if assist_requested:
        pre_lease_snapshot = git.capture_task_mutation_snapshot(
            ref.path,
            extra_paths=(log_path(cfg),),
            union_paths=(log_path(cfg),),
        )
    else:
        pre_lease_snapshot = git.FileMutationRollback.capture(
            (ref.ticket_path, log_path(cfg)),
            union_paths=(log_path(cfg),),
        )
    ticket_bytes = pre_lease_snapshot.originals[ref.ticket_path]
    if ticket_bytes is None:
        _bail(f"Task {ref.id_slug} has no ticket.md. Cannot advance.")
    ticket = Ticket.parse(ticket_bytes.decode("utf-8"))

    # A forward bump finishes work, so it requires a ticket that is being
    # worked on. A rewind only repositions `step:` and never touches `status:`,
    # so it also accepts the statuses a human can rewind from without first
    # launching the ticket just to flip it to `in_progress`.
    if rewind:
        reason = rewind_status_error(ref.id_slug, ticket.status)
        if reason:
            _bail(reason)
    elif ticket.status != "in_progress":
        _bail(f"Task {ref.id_slug} is {ticket.status!r}. Cannot advance.")

    _assert_supervised_step_is_current(ref, ticket.step)

    # Hand-authored / pre-freeze tickets carry `workflow:` as a bare string
    # ref instead of the frozen dict create produces. Resolve and freeze
    # in-place so the rest of bump (and future bumps) sees a normal shape.
    if isinstance(ticket.workflow, str):
        try:
            wf_def = Workflow.load(resolve_workflow_path(cfg, ticket.workflow))
        except WorkflowError as exc:
            _bail(str(exc))
        ticket.frontmatter["workflow"] = wf_def.freeze()
        if not ticket.step:
            ticket.frontmatter["step"] = f"1 ({wf_def.steps[0].name})"
        try:
            if assist_requested:
                # The strict mutation must remain one exact transaction. Keep
                # the frozen workflow in memory until the final step/done
                # writer consumes the pre-lease ticket snapshot.
                assert_task_valid(
                    cfg,
                    ref,
                    action="freeze workflow on bump",
                    ticket_override=ticket,
                )
            else:
                ticket.write(ref.ticket_path)
                assert_task_valid(cfg, ref, action="freeze workflow on bump")
        except TaskValidationError as exc:
            _bail(str(exc))

    wf = ticket.workflow

    if not wf or not wf.get("steps"):
        _bail(
            f"Task {ref.id_slug} has no workflow. "
            f"Run `coga mark done {ref.id_slug}` to finish."
        )

    steps = wf["steps"]
    total = len(steps)
    current_idx = ticket.step_index() or 0
    if current_idx > total:
        _bail(
            f"Task {ref.id_slug} has invalid step {ticket.step!r}. "
            f"Workflow has steps 1-{total}."
        )
    finish = False
    if backward:
        next_step = current_idx - 1
        if current_idx <= 1:
            _bail(f"Task {ref.id_slug} is on the first step. Cannot rewind.")
    elif to_step is not None:
        next_step = to_step
        if to_step < 1 or to_step > total:
            _bail(f"Unknown step {to_step}. Workflow has steps 1-{total}.")
        if to_step == current_idx:
            _bail(f"Task {ref.id_slug} is already on step {to_step}.")
        if to_step > current_idx:
            _bail("Cannot skip ahead with --to. Use `coga bump` to advance one step.")
    else:
        next_step = current_idx + 1
        finish = current_idx >= total

    # Completion gate: refuse to advance *off* a step that declares `requires:`
    # until its artifact is recorded on the blackboard. Forward advancement only
    # — a human rewind (--to/--backward) is never gated. This is a data check
    # (`coga/step_gate`), not an exit-code check: a step like `open-pr` that
    # declares `requires: pr` cannot be bumped past until `coga open-pr` has
    # written `pr:` under `## Dev`.
    publish_current_branch = False
    if not rewind and 1 <= current_idx <= total:
        requires = steps[current_idx - 1].get("requires")
        if requires is not None:
            # A missing blackboard fence means no artifact is recorded, so the
            # gate should block (not raise) — validate flags the fence itself.
            blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
            reason = gate_unmet_reason(requires, blackboard, slug=ref.id_slug)
            if reason:
                _bail(reason)
            publish_current_branch = gate_publishes_current_branch(requires)

    # Only terminal bump delegates to an outcome writer that may append the
    # digest spool. Add that possible leaf to the original snapshot now — still
    # before the network lease — without making ordinary step advances own it.
    spool_path = None
    if finish and assist_requested:
        state_snapshot = read_snapshot(ref.path)
        if state_snapshot is not None:
            parent_ticket = parent_ticket_path(cfg, state_snapshot)
            if parent_ticket.parent.is_dir():
                pre_lease_snapshot.originals[parent_ticket] = (
                    parent_ticket.read_bytes()
                    if parent_ticket.is_file()
                    else None
                )
        spool_path = digest_spool_target_path(cfg)
        if spool_path is not None:
            pre_lease_snapshot.originals[spool_path] = (
                spool_path.read_bytes() if spool_path.is_file() else None
            )
            pre_lease_snapshot.union_paths = frozenset(
                (*pre_lease_snapshot.union_paths, spool_path)
            )

    if assist_requested and (
        (finish and spool_path is None) or (not finish and message is not None)
    ):
        try:
            preflight_post(cfg)
        except typer.Exit:
            _bail(
                f"Could not advance {ref.id_slug} from the recorded assist: "
                "notification configuration must be valid before strict "
                "state publication.",
                exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
            )

    try:
        assist = (
            pr_assist.assist_publication_from_env(
                cfg,
                ref,
                mutation_snapshot=pre_lease_snapshot,
            )
            if assist_requested
            else None
        )
    except git.FeaturePublicationError as exc:
        _bail(
            f"Could not verify the recorded assist branch before advancing "
            f"{ref.id_slug}: {exc}",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    if assist_requested and assist is None:
        _bail(
            f"Could not rebuild {ref.id_slug}'s recorded assist capability.",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    assist_publication = assist.lease if assist is not None else None
    assist_guard = assist.guard if assist is not None else None
    rollback = pre_lease_snapshot if assist is not None else None
    publication_succeeded = False

    def record_publication() -> None:
        nonlocal publication_succeeded
        publication_succeeded = True

    if finish:
        effective_assignee = assist.agent if assist is not None else ticket.assignee
        finisher = effective_assignee or cfg.current_user
        actor = (
            f"agent:{effective_assignee}"
            if assist is not None
            else f"human:{cfg.current_user}"
        )
        prev = ticket.current_step()
        transition = f": {prev['name']} → done" if prev else ""
        try:
            mark_done(
                cfg,
                ref,
                ticket,
                actor=actor,
                log_message=f"task done{suffix}",
                slack_text=(
                    f"🎉 {finisher} finished *{ref.id_slug}* "
                    f'"{ticket.title}"{transition}{suffix}'
                ),
                digest_detail=(
                    f"{finisher} finished{transition or ' → done'} ✅{suffix}"
                ),
                image_url=cfg.gif_for("done"),
                echo=f"{ref.id_slug}: done",
                force=force,
                publish_current_branch=publish_current_branch,
                feature_publication=assist_publication,
                feature_publication_guard=assist_guard,
                mutation_snapshot=rollback,
                after_sync=record_publication if rollback is not None else None,
            )
        except git.FeaturePublicationError as exc:
            _bail_strict_transition(
                ref,
                "done",
                exc,
                rollback,
                publication_succeeded=publication_succeeded,
            )
        except StrandedProductCode as exc:
            if rollback is not None:
                _bail_strict_transition(
                    ref,
                    "done",
                    exc,
                    rollback,
                    publication_succeeded=publication_succeeded,
                )
            listed = "\n".join(f"    {path}" for path in exc.paths)
            _bail(
                f"Cannot finish {ref.id_slug}: its {exc.workflow_name} workflow "
                f"has no push/PR step, but this checkout committed tracked "
                f"product code that is not on {cfg.git_control_branch!r}:\n"
                f"{listed}\n"
                f"That code will strand off the control branch if this checkout "
                f"or its branch is removed. Move the ticket to a code/* workflow "
                f"(code/with-self-review or code/with-review) so it opens a PR, "
                f"or re-run `coga bump {ref.id_slug} --force` to finish anyway "
                f"and keep the code stranded."
            )
        except TaskValidationError as exc:
            if rollback is not None:
                _bail_strict_transition(
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
                ref,
                "done",
                exc,
                rollback,
                publication_succeeded=publication_succeeded,
            )

        if os.environ.get("COGA_SUPERVISED"):
            typer.secho(
                "Supervised launch: final step done. The task is finished "
                "— coga launch will stop and return to the caller.",
                fg=typer.colors.CYAN,
            )
        emit_done_marker(session_id=ref.id_slug)
        return

    new_step = steps[next_step - 1]
    new_step_name = new_step["name"]
    prev_step_name = (
        steps[current_idx - 1]["name"] if current_idx >= 1 else f"step {current_idx}"
    )

    role = new_step.get("assignee")
    new_assignee: str | None = None
    if role is not None:
        try:
            resolved = resolve_step_assignee(cfg, ticket, role)
        except AssigneeResolutionError as exc:
            _bail(str(exc))
        if resolved != ticket.assignee:
            new_assignee = resolved

    handoff = f" → assigned to {new_assignee}" if new_assignee else ""

    if rewind:
        actor = f"human:{cfg.current_user}"
        finisher = cfg.current_user
        verb = "rewound"
    elif assist is not None:
        actor = f"agent:{assist.agent}"
        finisher = assist.agent
        verb = "advanced"
    else:
        actor = f"agent:{ticket.assignee}" if ticket.assignee else f"human:{cfg.current_user}"
        finisher = ticket.assignee or cfg.current_user
        verb = "advanced"

    # The assignee the supervisor will see after this bump: the freshly
    # resolved one if the step changed it, else the unchanged current assignee.
    # Captured before `advance_step` so it can't be perturbed by the write.
    next_assignee = new_assignee if new_assignee is not None else ticket.assignee

    try:
        advance_step(
            cfg, ref, ticket,
            next_step=next_step,
            new_step_name=new_step_name,
            actor=actor,
            log_message=f"{verb} to step {next_step} ({new_step_name}){handoff}{suffix}",
            slack_text=(
                f"👉 {finisher} {verb} *{ref.id_slug}* \"{ticket.title}\": "
                f"{prev_step_name} → {new_step_name} "
                f"(step {next_step}/{total}){handoff}{suffix}"
            ),
            digest_detail=(
                f"{finisher} {verb}: {prev_step_name} → {new_step_name} "
                f"(step {next_step}/{total}){handoff}{suffix}"
            ),
            new_assignee=new_assignee,
            notify_slack=message is not None,
            echo=f"{ref.id_slug}: step {next_step} ({new_step_name}){handoff}",
            rewind=rewind,
            publish_current_branch=publish_current_branch,
            feature_publication=assist_publication,
            feature_publication_guard=assist_guard,
            mutation_snapshot=rollback,
            after_sync=record_publication if rollback is not None else None,
        )
    except git.FeaturePublicationError as exc:
        _bail_strict_transition(
            ref,
            f"step {next_step} ({new_step_name})",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )
    except TaskValidationError as exc:
        if rollback is not None:
            _bail_strict_transition(
                ref,
                f"step {next_step} ({new_step_name})",
                exc,
                rollback,
                publication_succeeded=publication_succeeded,
            )
        _bail(str(exc))
    except BaseException as exc:
        if rollback is None:
            raise
        _bail_strict_transition(
            ref,
            f"step {next_step} ({new_step_name})",
            exc,
            rollback,
            publication_succeeded=publication_succeeded,
        )

    # When this bump ran inside a supervised `coga launch`, the supervisor
    # tears down the agent's REPL via the done marker (see
    # `emit_done_marker` below) and then decides whether to chain. Tell the
    # human what happens next so a long-running interactive session isn't
    # surprising.
    if os.environ.get("COGA_SUPERVISED"):
        # Mirror `_harness_stop_reason` (launch.py): the supervisor chains
        # whenever the next step's assignee is a configured agent — including an
        # agent *rotation* (e.g. claude -> codex for peer review) — and only
        # returns control to the caller when the next step hands off to a human
        # (an assignee that is not a configured agent type) or is unassigned.
        # The old `new_assignee is None` check wrongly framed every rotation as
        # a stop, so a claude -> codex bump printed "will stop" while the
        # supervisor actually chained.
        will_chain = bool(next_assignee) and next_assignee in cfg.agents
        if will_chain:
            hint = (
                "Supervised launch: step done. coga launch will spawn "
                "a fresh agent session for the next step."
            )
        else:
            who = next_assignee or "an unassigned step"
            hint = (
                f"Supervised launch: step done. Next step hands off to {who} "
                "— coga launch will stop and return to the caller."
            )
        typer.secho(hint, fg=typer.colors.CYAN)

    # Tell a supervising `coga launch` the session is done so the agent's
    # REPL tears down without `/exit`. Harmless tagged line otherwise. The
    # task's `id_slug` scopes the signal to this ticket so an unrelated nested
    # `coga bump` (e.g. a test fixture) can't end our session. It is the
    # *slug*, not the resolved path, on purpose: the same ticket can live at
    # two absolute paths (e.g. a peer agent's separate clone or another
    # checkout of the repo), so a path-scoped marker written from the "wrong"
    # cwd never matched what the supervisor polled for and the REPL hung. The
    # slug is identical from any checkout.
    emit_done_marker(session_id=ref.id_slug)


def _bail_strict_transition(
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
        refused = rollback.restore()
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


def _bail(msg: str, *, exit_code: int = 2) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(exit_code)


def _assert_supervised_step_is_current(
    ref: TaskRef, current_step: str | None
) -> None:
    """Refuse stale supervised bumps.

    `coga launch` composes one prompt for one ticket step. If a second launch
    chain has already advanced that same ticket, this session's context is stale
    and bumping again would silently skip or duplicate work. Scope the check to
    the launched task path so inherited env vars do not affect nested fixtures
    or another task's bump.
    """
    if not os.environ.get("COGA_SUPERVISED"):
        return
    expected_task = os.environ.get(EXPECTED_TASK_ENV)
    expected_step = os.environ.get(EXPECTED_STEP_ENV)
    if not expected_task or expected_step is None:
        return
    try:
        expected_path = os.path.realpath(expected_task)
        actual_path = os.path.realpath(str(ref.path))
    except OSError:
        return
    if expected_path != actual_path:
        return
    if (current_step or "") == expected_step:
        return

    actual = current_step or "<no step>"
    expected = expected_step or "<no step>"
    _bail(
        f"Refusing to bump {ref.id_slug}: this session was composed for "
        f"step {expected!r}, but the ticket is now on step {actual!r}. "
        "Another session may have already advanced it; relaunch before "
        "bumping from stale context."
    )
