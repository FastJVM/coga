"""`coga retire` — run Retro against a done task."""

from __future__ import annotations

import sys

import typer

from coga import git
from coga.blackboard import append_blocker
from coga.autoclose import (
    parse_branch_name,
    parse_branch_names,
    parse_pr_url,
    parse_worktree_path,
)
from coga.branchcleanup import WorktreeCleanupResult
from coga.checkout_disposal import CheckoutDisposal, dispose_checkout
from coga.config import Config, ConfigError, load_config
from coga.create import create_task
from coga.git import GitError
from coga.mark import mark_blocked
from coga.paths import RepoResourceUnreadable, load_resource
from coga.retire_worklist import RetireWorklistError, discharge_slug
from coga.slugify import slugify
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import (
    TaskRef,
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)
from coga.validate import TaskValidationError


def retire(
    task: str = typer.Argument(..., help="Done task ID or id-slug to retire."),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Agent nickname to assign. Defaults to the current user's first configured agent.",
    ),
    no_launch: bool = typer.Option(
        False,
        "--no-launch",
        help="Create the retire task but do not launch it.",
    ),
) -> None:
    """Wrap up a done task by running retro/done-ticket against it.

    Validates the named task is `status: done`, then creates a one-shot
    ad-hoc task whose body invokes the `retro/done-ticket` skill against it.
    The retro skill opens a PR when it extracts new durable knowledge; that PR
    records the `## Retro` marker, edits the knowledge base, and deletes the
    source task directory in the same PR. If no new durable knowledge exists,
    Retro direct-deletes the task via `coga delete` (no PR, no marker; recover
    with `git restore`).

    Before launching that retro pass, retire disposes of the ticket's feature
    checkout and git branch, both read from the `## Dev` blackboard section
    while the ticket (and thus the `worktree:` / `branch:` lines) still exists.
    The recorded linked worktree is removed first — which also unpins the branch
    Git would otherwise refuse to delete — then the local branch and its
    `origin` counterpart. This is the manual lifecycle event that disposes of
    both; the daily autoclose sweep runs the same shared proofs
    (`coga.checkout_disposal`) for the tickets it closes. The worktree removal
    requires an exact, unshared, locally pristine linked checkout of this same
    repository, and the remote branch delete is gated on the linked PR being
    merged at the current exact head with no other open PR for that branch.
    Claims from sibling Coga workspaces in the same Git checkout count as
    shared. It never removes the invoking checkout, `main`, or an unrelated
    branch. (This deliberately overrides the former punt that branch hygiene
    was a Dream concern — that punt is why branches and worktrees piled up.)
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    typer.echo(f"Retire: target task {ref.id_slug} at {ref.path}")
    source = read_ticket(ref)
    if source.status != "done":
        _bail(
            f"Retire only operates on done tickets — {ref.id_slug} is "
            f"{source.status!r}. Bump it to done first."
        )

    # Prune the ticket's worktree and branches while the task (and its `## Dev`
    # `worktree:`/`branch:`/`pr:` lines) still exists — the retro pass below
    # deletes the directory. Anything the proofs kept is a bug: the ticket is
    # the checkout's only owner record, so the retire task below is created
    # blocked and Retro never runs.
    disposal = _cleanup_checkout(cfg, ref)
    refusal = _kept_checkout_refusal(disposal)
    checkout = disposal.worktree_result if disposal is not None else None
    if refusal is None:
        _discharge_worklist_entry(cfg, ref)

    try:
        main_agent = agent or _default_agent(cfg)
        agent_type = cfg.agent_type(main_agent)
    except ConfigError as exc:
        _bail(str(exc))
    typer.echo(
        f"Retire: using main agent {main_agent} "
        f"(agent type {agent_type.name})"
    )

    title = f"Retire {ref.id_slug}"
    slug_override = f"retire-{slugify(ref.id_slug)}"
    try:
        typer.echo(f"Retire: creating task {title!r}")
        result = create_task(
            cfg=cfg,
            title=title,
            # Retire creates straight to `active`; every task past `draft`
            # carries a workflow, so it runs its body through the one-step
            # `direct/body` workflow rather than being a workflow-less active
            # task the validator (rightly) rejects as un-bumpable.
            workflow_name="direct/body",
            contexts=[],
            owner=cfg.current_user,
            agent=main_agent,
            status="active",
            slug_override=slug_override,
            description=_retire_body(cfg, ref.id_slug, checkout, refusal),
            created_by="retire",
        )
    except (
        ConfigError, TaskValidationError, ValueError, RepoResourceUnreadable,
    ) as exc:
        _bail(str(exc))

    slug = result["slug"]
    created = TaskRef(slug=slug, path=result["path"])
    typer.echo(f"Retire: created task {slug} at {result['path']} (active)")
    typer.echo(f"Created {slug}")
    git.sync_task_state(
        cfg, created.path, message=f"Ticket: {created.id_slug} — created (retire)"
    )
    if refusal is not None:
        _block_retire_task(cfg, resolve_task(cfg, slug), refusal)
    if no_launch:
        typer.echo("Retire: launch skipped (--no-launch)")
        typer.echo(f"Run `coga launch {slug}` to start the retire pass.")
        return

    typer.echo(f"Retire: launching {slug}")
    from coga.commands.launch import launch

    launch(
        slug,
        agent_override=None,
        prompt_report=False,
    )


def _cleanup_checkout(cfg: Config, ref: TaskRef) -> CheckoutDisposal | None:
    """Remove the retiring ticket's linked worktree and branch, best-effort.

    Reads the `## Dev` blackboard section (still present pre-retro) and hands
    its `branch:` / `worktree:` / `pr:` values to
    `checkout_disposal.dispose_checkout`, which runs the live-claim scan, then
    the worktree removal, then the branch deletion. Any failure — `git`/`gh`
    missing, a read error, git not enabled — is reported and swallowed:
    checkout hygiene is a courtesy on top of retire, not a precondition for it.

    Returns the disposal, so the caller can refuse on owned branches the
    sweep kept and carry a *preserved* checkout into the retro task body — see
    `_checkout_cleanup_section`. Returns `None` whenever cleanup was skipped.
    """
    if not cfg.git_enabled:
        return None
    try:
        root = git.toplevel(ref.ticket_path)
        if root is None:
            return None
        current_branch = git.current_branch(root)
        if current_branch != cfg.git_control_branch:
            typer.echo(
                "Retire: checkout cleanup skipped "
                f"(run from {cfg.git_control_branch!r}; current checkout is "
                f"{current_branch!r})."
            )
            return None
        blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
    except (GitError, OSError, TaskFileError) as exc:
        typer.echo(f"Retire: checkout cleanup skipped ({exc}).")
        return None
    return dispose_checkout(
        cfg,
        root,
        branch=parse_branch_name(blackboard),
        worktree=parse_worktree_path(blackboard),
        pr_url=parse_pr_url(blackboard),
        echo=typer.echo,
        owned_branches=parse_branch_names(blackboard),
    )


def _kept_checkout_refusal(disposal: CheckoutDisposal | None) -> str | None:
    """The blocker reason when cleanup kept a worktree or branch, else None."""
    if disposal is None or disposal.disposed:
        return None
    kept = []
    if disposal.claim is not None or not disposal.worktree_gone:
        if disposal.worktree:
            kept.append(f"worktree `{disposal.worktree}`")
    names = [*disposal.branches_remaining]
    if disposal.branch and (disposal.local_branch_remains or disposal.claim):
        names.insert(0, disposal.branch)
    kept.extend(f"branch `{name}`" for name in dict.fromkeys(names))
    what = ", ".join(kept) or "the checkout"
    return f"Retire kept {what}; this is a bug, fix by hand. {disposal.reason}"


def _block_retire_task(cfg: Config, created: TaskRef, reason: str) -> None:
    """Block the fresh retire task over a kept checkout and exit non-zero.

    Retro would delete the source ticket, the checkout's only owner record, so
    it must not run. Blocking notifies the owner on Slack like `coga block`;
    they fix the branch by hand, then `coga unblock` and launch the task.
    """
    actor = f"human:{cfg.current_user}"
    try:
        with git.state_lock(cfg):
            append_blocker(created.ticket_path, actor, reason)
        ticket = read_ticket(created)
        mark_blocked(
            cfg,
            created,
            ticket,
            actor=actor,
            log_message=f"blocked: {reason}",
            slack_text=f"🛑 retire blocked *{created.id_slug}*: {reason}",
            image_url=cfg.gif_for("block") or cfg.gif_for("panic"),
            echo=f"{created.id_slug}: blocked (launch skipped)",
        )
    except TaskValidationError as exc:
        _bail(str(exc))
    _bail(
        f"Retire refused: {reason} Fix it, then `coga unblock {created.id_slug}` "
        f"and `coga launch {created.id_slug}`."
    )


def _discharge_worklist_entry(cfg: Config, ref: TaskRef) -> None:
    """Drop this slug from the autoclose retire worklist once its checkout is gone.

    Best effort, like the cleanup above: never abort retire over it. Only a
    checkout that is really gone loses its line — see `discharge_slug` and the
    `coga/autoclose/sweep` skill for what happens to a preserved one.
    """
    try:
        root = git.toplevel(ref.ticket_path)
        if root is None:
            return
        for path in discharge_slug(cfg, ref.id_slug, root=root):
            typer.echo(f"Retire: dropped {ref.id_slug} from {path}.")
    except (GitError, OSError, UnicodeError, RetireWorklistError) as exc:
        typer.echo(f"Retire: retire worklist not updated ({exc}).")


def _default_agent(cfg: Config) -> str:
    default = cfg.default_agent()
    if default is None:
        raise ConfigError(
            "No agent types declared in [agents]. Pass --agent or declare "
            "at least one `[agents.*]` table in coga.toml or coga.local.toml."
        )
    return default.name


def _retire_body(
    cfg: Config,
    target_slug: str,
    checkout: WorktreeCleanupResult | None = None,
    refusal: str | None = None,
) -> str:
    template, override = load_resource(cfg, "retire.md")
    try:
        body = template.format(slug=target_slug).strip()
    except (KeyError, IndexError, ValueError, AttributeError) as exc:
        if override is None:
            raise
        # `retire.md` renders with `str.format`, so a stray brace in a repo
        # override must name the file rather than surface as a bare KeyError.
        raise RepoResourceUnreadable(
            f"repo resource override {override} is not a valid `retire.md` "
            f"template ({type(exc).__name__}: {exc}); only `{{slug}}` is "
            "substituted — double any literal brace as `{{` / `}}`"
        ) from exc
    section = _checkout_cleanup_section(checkout)
    if section:
        body = f"{body}\n\n{section}"
    if refusal:
        body = (
            f"{body}\n\n### Kept checkout\n\n{refusal}\n\nThis task was "
            "created blocked. Do not run Retro until the checkout is gone."
        )
    return body


def _checkout_cleanup_section(checkout: WorktreeCleanupResult | None) -> str:
    """A durable record of a feature checkout retire refused to remove.

    Retire's cleanup notes are echoed to a terminal that immediately scrolls
    under the retro launch two lines later, which is most of why a preserved
    checkout goes unnoticed until someone audits by hand. When one survives,
    carry the reason and the exact manual command into the retro task body so
    they outlive the scrollback. Nothing to say when the worktree was removed,
    or when no worktree was recorded.
    """
    if (
        checkout is None
        or checkout.worktree is None
        or checkout.removed
        or checkout.already_gone
    ):
        return ""
    notes = "\n".join(f"- {note}" for note in checkout.notes)
    return (
        "### Checkout cleanup\n\n"
        f"Retire left the feature checkout `{checkout.worktree}` in place, with "
        "the reason below. This is a note for the human, not a step: do not act "
        "on it during the retro pass.\n\n"
        f"{notes}"
    )


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
