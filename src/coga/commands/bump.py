"""`coga bump` — move through a workflow."""

from __future__ import annotations

import os
import sys

import typer

from coga import git, pr_assist
from coga.commands.common import completion_identity, current_operator
from coga.bump import (
    OperatorResolutionError,
    advance_step,
    resolve_operator,
    rewind_status_error,
)
from coga.config import ConfigError, load_config
from coga.mark import StrandedProductCode, mark_done
from coga.notification import preflight_post
from coga.paths import resolve_workflow_path
from coga.step_gate import gate_unmet_reason
from coga.taskfile import read_blackboard
from coga.task_env import is_script_task
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

    if rewind and is_script_task(ref):
        _bail(
            "Ticket scripts cannot rewind. A human can rewind outside the "
            "script with `coga bump <id> --to <step>`."
        )

    try:
        assist = pr_assist.assist_session_from_env(cfg, ref)
    except git.GitError as exc:
        _bail(f"Could not rebuild {ref.id_slug}'s recorded assist session: {exc}")
    if rewind and assist is not None:
        _bail(
            "Agents cannot rewind from a recorded assist. Call `coga block "
            "--task <id> --reason \"...\"`; a human can rewind outside the "
            "assist with `coga bump <id> --to <step>`."
        )
    if not ref.ticket_path.is_file():
        _bail(f"Task {ref.id_slug} has no ticket.md. Cannot advance.")
    ticket = Ticket.parse(ref.ticket_path.read_text(encoding="utf-8"))

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
            git.write_ticket(cfg, ticket, ref.ticket_path)
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
    if not rewind and 1 <= current_idx <= total:
        requires = steps[current_idx - 1].get("requires")
        if requires is not None:
            # A missing blackboard fence means no artifact is recorded, so the
            # gate should block (not raise) — validate flags the fence itself.
            blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
            reason = gate_unmet_reason(requires, blackboard, slug=ref.id_slug)
            if reason:
                _bail(reason)
        # Advisory only, after the gate: a stranded ticket write on the
        # recorded feature branch is named now, while it is still cheap to fix.
        _warn_stranded_task_state(cfg, ref)

    # Every bump that will post live — the terminal outcome, or a step advance
    # carrying --message — validates the notification configuration *before*
    # the mutation. `mark_done` / `bump_step` announce with `fatal=False`, so
    # an unresolved webhook found after the write is reported and dropped, not
    # a crash; the only place it can still refuse is here.
    if finish or message is not None:
        preflight_post(cfg)

    if finish:
        actor, finisher = completion_identity(
            cfg, ref, ticket, assist_agent=assist.agent if assist else None
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
                image_url=cfg.gif_for("done"),
                echo=f"{ref.id_slug}: done",
                force=force,
            )
        except StrandedProductCode as exc:
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
            _bail(str(exc))

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

    # Derive both the current and the prospective next operator before moving.
    # Refusing here keeps a role that cannot resolve on this machine from
    # advancing the ticket on disk with no audit entry and no sync — and the
    # answer is only reported, never written: `advance_step` has no assignment
    # to persist.
    holder = current_operator(cfg, ref, ticket)
    try:
        next_operator = resolve_operator(cfg, ref, ticket, step_index=next_step)
    except OperatorResolutionError as exc:
        _bail(str(exc))
        return
    next_agent = next_operator.name if next_operator is not None else None

    # An active/paused rewind must still be resumable with `coga launch`.
    # Normal launch intentionally refuses an owner handoff, while a forward bump
    # intentionally requires `in_progress`; accepting this combination would
    # therefore strand the target step. An already in-progress human handoff
    # remains valid and can be completed normally.
    if (
        rewind
        and ticket.status in {"active", "paused"}
        and (next_operator is None or next_operator.is_human)
    ):
        target = "unrouted" if next_operator is None else repr(next_operator.name)
        _bail(
            f"Cannot rewind {ref.id_slug} from {ticket.status!r} to step "
            f"{next_step} ({new_step_name}): the target is not agent-owned "
            f"({target}). Only an in_progress ticket can rewind to a human "
            "handoff."
        )

    handoff = (
        f" → {next_agent}"
        if next_agent is not None and next_agent != holder
        else ""
    )

    if rewind:
        actor = f"human:{cfg.current_user}"
        finisher = cfg.current_user
        verb = "rewound"
    else:
        actor, finisher = completion_identity(
            cfg, ref, ticket, assist_agent=assist.agent if assist else None
        )
        verb = "advanced"

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
            notify_slack=message is not None,
            echo=f"{ref.id_slug}: step {next_step} ({new_step_name}){handoff}",
            rewind=rewind,
        )
    except git.StateRegressionError as exc:
        _bail(
            f"Could not publish {ref.id_slug}'s rewind because control state "
            f"changed: {exc}. The local rewind was retained for inspection. "
            "Reconcile this checkout with control before running any other "
            "mutating Coga command here, then retry.",
            exit_code=git.RETRY_WITHOUT_SWEEP_EXIT_CODE,
        )
    except TaskValidationError as exc:
        _bail(str(exc))

    # When this bump ran inside a supervised `coga launch`, the supervisor
    # tears down the agent's REPL via the done marker (see
    # `emit_done_marker` below) and then decides whether to chain. Tell the
    # human what happens next so a long-running interactive session isn't
    # surprising.
    if os.environ.get("COGA_SUPERVISED"):
        # Mirror `_harness_stop_reason` (launch.py): the supervisor chains
        # whenever the next step routes to an agent — including a main <-> peer
        # rotation — and only returns control to the caller when the next step
        # hands off to the owner. The discriminator is the derived operator's
        # role, so a claude -> codex rotation correctly reads as "will chain".
        if next_operator is not None and next_operator.is_agent:
            hint = (
                "Supervised launch: step done. coga launch will spawn "
                "a fresh agent session for the next step."
            )
        else:
            who = "an unrouted step" if next_operator is None else next_operator.name
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


def _bail(msg: str, *, exit_code: int = 2) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(exit_code)


def _warn_stranded_task_state(cfg: Config, ref: TaskRef) -> None:
    """Advisory: name a ticket write the recorded feature branch has stranded.

    Runs on every forward bump whose blackboard records a usable `branch:`, in
    the separate-checkout layout only. `coga open-pr` refuses the same state a
    step later, but its refusal arrives after the agent has moved on and — if
    the branch is rebased first — not at all. Here the comparison is still
    cheap: both refs live in this repository, so no `worktree:` pointer is
    followed and no other checkout is read.

    The layout exemption is a *diagnostic* rule for tickets from the retired
    single-checkout layout: when this checkout is standing on the recorded
    branch, or the recorded worktree resolves to this same checkout, the
    committed ticket on that branch was the live copy, so nothing is said. Erring toward silence is the right failure
    for a warning.

    Never blocks, never changes the exit code, never writes to the ticket or
    the log. Every probe — blackboard read, layout lookup, comparator — sits
    inside the boundary below, so a missing ref, a foreign `/tmp` clone whose
    branch this repository has never seen, or an unusable `git` is silent.
    Writes to stderr only; several commands parse bump's stdout.
    """
    try:
        from coga.autoclose import parse_branch_name, parse_worktree_path
        from coga.github_preflight import (
            stranded_task_state_paths,
            stranded_task_state_remediation,
        )
        from coga.open_pr import same_git_checkout

        blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
        branch = parse_branch_name(blackboard)
        if not branch or branch.startswith("("):
            return
        root = cfg.repo_root
        if git.current_branch(root) == branch:
            return
        worktree = parse_worktree_path(blackboard)
        if worktree and same_git_checkout(root, worktree):
            return
        toplevel = git.toplevel(root)
        if toplevel is None:
            return
        ticket_rel = ref.ticket_path.resolve().relative_to(toplevel).as_posix()
        control = cfg.git_control_branch
        # Fully qualified on both sides: a bare name resolves `refs/tags/<name>`
        # before `refs/heads/<name>`, so a tag named like the branch would make
        # the probe compare the wrong commit and suppress the warning.
        control_ref = f"refs/heads/{control}"
        branch_ref = f"refs/heads/{branch}"
        stranded = stranded_task_state_paths(
            control_ref, branch_ref, [ticket_rel], cwd=toplevel
        )
        if not stranded:
            return
        remediation = stranded_task_state_remediation(
            control_ref=control_ref,
            branch_ref=branch_ref,
            paths=stranded,
            checkout=worktree,
        )
        sys.stderr.write(
            f"[bump] Branch {branch!r} has committed changes to this ticket's "
            f"own file ({', '.join(stranded)}) that {control} does not contain "
            "— a stranded ticket write. `coga open-pr` will refuse this branch, "
            "and a rebase would replay the commit into a merge conflict. "
            f"{remediation}\n"
        )
    except Exception:  # advisory only — never fail the bump
        return


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
