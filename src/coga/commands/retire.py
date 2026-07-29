"""`coga retire` — run Retro against a done task."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from coga import git
from coga.autoclose import parse_branch_name, parse_worktree_path
from coga.branchcleanup import delete_ticket_branch, remove_ticket_worktree
from coga.config import Config, ConfigError, load_config
from coga.create import create_task
from coga.git import GitError
from coga.lifecycle import TERMINAL_STATUSES
from coga.paths import read_packaged_resource
from coga.slugify import slugify
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import (
    TaskRef,
    TaskNotFoundError,
    list_tasks,
    read_ticket,
    resolve_task,
)
from coga.ticket import TicketError
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
    `origin` counterpart. This is the lifecycle event that disposes of both: the
    worktree removal requires an exact, unshared, locally pristine linked
    checkout of this same repository, and the remote branch delete is gated on
    the linked PR being merged at the current exact head. It never removes the
    invoking checkout, `main`, or an unrelated branch. (This deliberately
    overrides the former punt that branch hygiene was a Dream concern — that
    punt is why branches and worktrees piled up.)
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

    # Prune the ticket's worktree and branch while the task (and its `## Dev`
    # `worktree:`/`branch:`/`pr:` lines) still exists — the retro pass below
    # deletes the directory. Best effort: a cleanup failure must never abort the
    # retire run.
    _cleanup_checkout(cfg, ref)

    try:
        assignee = agent or _default_agent(cfg)
        agent_type = cfg.agent_type(assignee)
    except ConfigError as exc:
        _bail(str(exc))
    typer.echo(
        f"Retire: using assignee {assignee} "
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
            assignee=assignee,
            watchers=[],
            status="active",
            slug_override=slug_override,
            description=_retire_body(ref.id_slug),
            created_by="retire",
        )
    except (ConfigError, TaskValidationError, ValueError) as exc:
        _bail(str(exc))

    slug = result["slug"]
    created = TaskRef(slug=slug, path=result["path"])
    typer.echo(f"Retire: created task {slug} at {result['path']} (active)")
    typer.echo(f"Created {slug}")
    git.sync_task_state(
        cfg, created.path, message=f"Ticket: {created.id_slug} — created (retire)"
    )
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


def _cleanup_checkout(cfg: Config, ref: TaskRef) -> None:
    """Remove the retiring ticket's linked worktree and branch, best-effort.

    Reads the `## Dev` blackboard section (still present pre-retro) and hands it
    to `branchcleanup.remove_ticket_worktree`, then
    `branchcleanup.delete_ticket_branch`. The worktree goes first so a branch it
    holds is no longer checked out when branch cleanup runs. Any failure —
    `git`/`gh` missing, a read error, git not enabled — is reported and
    swallowed: checkout hygiene is a courtesy on top of retire, not a
    precondition for it.
    """
    if not cfg.git_enabled:
        return
    try:
        root = git._toplevel(ref.ticket_path)
        if root is None:
            return
        current_branch = git._current_branch(root)
        if current_branch != cfg.git_control_branch:
            typer.echo(
                "Retire: checkout cleanup skipped "
                f"(run from {cfg.git_control_branch!r}; current checkout is "
                f"{current_branch!r})."
            )
            return
        blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
    except (GitError, OSError, TaskFileError) as exc:
        typer.echo(f"Retire: checkout cleanup skipped ({exc}).")
        return
    try:
        claim = _live_checkout_claim(cfg, ref, root, blackboard)
    except Exception as exc:  # noqa: BLE001 — incomplete proof preserves checkout
        typer.echo(
            "Retire: checkout cleanup skipped "
            f"(could not verify other live ticket claims: {exc})."
        )
        return
    if claim is not None:
        typer.echo(f"Retire: checkout cleanup skipped ({claim}).")
        return
    try:
        remove_ticket_worktree(cfg, root, blackboard, echo=typer.echo)
    except Exception as exc:  # noqa: BLE001 — never let cleanup abort retire
        typer.echo(f"Retire: worktree cleanup failed ({exc}).")
    try:
        delete_ticket_branch(cfg, root, blackboard, echo=typer.echo)
    except Exception as exc:  # noqa: BLE001 — never let cleanup abort retire
        typer.echo(f"Retire: branch cleanup failed ({exc}).")


def _live_checkout_claim(
    cfg: Config,
    source_ref: TaskRef,
    root: Path,
    source_blackboard: str,
) -> str | None:
    """Describe another non-terminal ticket claiming this checkout, if any."""
    source_branch = parse_branch_name(source_blackboard)
    source_worktree = _normalized_worktree(root, source_blackboard)
    if source_branch is None and source_worktree is None:
        return None

    for other_ref in list_tasks(cfg):
        if other_ref.id_slug == source_ref.id_slug:
            continue
        try:
            other_ticket = read_ticket(other_ref)
        except (OSError, TicketError) as exc:
            raise RuntimeError(f"cannot read {other_ref.id_slug}: {exc}") from exc
        if other_ticket.status in TERMINAL_STATUSES:
            continue
        try:
            other_blackboard = read_blackboard(
                other_ref.ticket_path, blackboard_required=False
            )
        except (OSError, TaskFileError) as exc:
            raise RuntimeError(
                f"cannot read {other_ref.id_slug}'s blackboard: {exc}"
            ) from exc

        other_branch = parse_branch_name(other_blackboard)
        if source_branch is not None and other_branch == source_branch:
            return (
                f"live ticket {other_ref.id_slug!r} also records branch "
                f"{source_branch!r}"
            )
        other_worktree = _normalized_worktree(root, other_blackboard)
        if source_worktree is not None and other_worktree == source_worktree:
            return (
                f"live ticket {other_ref.id_slug!r} also records worktree "
                f"{str(source_worktree)!r}"
            )
    return None


def _normalized_worktree(root: Path, blackboard: str) -> Path | None:
    recorded = parse_worktree_path(blackboard)
    if recorded is None:
        return None
    path = Path(recorded).expanduser()
    if not path.is_absolute():
        path = root / path
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _default_agent(cfg: Config) -> str:
    default = cfg.default_agent()
    if default is None:
        raise ConfigError(
            "No agent types declared in [agents]. Pass --agent or declare "
            "at least one `[agents.*]` table in coga.toml."
        )
    return default.name


def _retire_body(target_slug: str) -> str:
    template = read_packaged_resource("retire.md")
    return template.format(slug=target_slug).strip()


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
