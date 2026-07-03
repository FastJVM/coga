"""`coga retire` — run Retro against a done task."""

from __future__ import annotations

import sys
from importlib.resources import files

import typer

from coga import git
from coga.branchcleanup import delete_ticket_branch
from coga.config import Config, ConfigError, load_config
from coga.create import create_task
from coga.git import GitError
from coga.slugify import slugify
from coga.taskfile import TaskFileError, read_blackboard
from coga.tasks import (
    TaskRef,
    TaskNotFoundError,
    read_ticket,
    resolve_task,
)


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

    Before launching that retro pass, retire prunes the ticket's git branch —
    the local branch and its `origin` counterpart — read from the `## Dev`
    blackboard section while the ticket (and thus the `branch:` line) still
    exists. This is the lifecycle event that disposes of the branch: the remote
    delete is gated on the linked PR being merged, never `main`, never an
    unrelated branch. (This deliberately overrides the former punt that branch
    hygiene was a Dream concern — that punt is why branches piled up.)
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

    # Prune the ticket's branch while the task (and its `## Dev` `branch:`/`pr:`
    # lines) still exists — the retro pass below deletes the directory. Best
    # effort: a branch-cleanup failure must never abort the retire run.
    _cleanup_branch(cfg, ref)

    try:
        assignee = agent or _default_agent(cfg)
        agent_type = cfg.agent_type(assignee)
    except ConfigError as exc:
        _bail(str(exc))
    typer.echo(
        f"Retire: using assignee {assignee} "
        f"(agent type {agent_type.name}, mode agent)"
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
            mode="agent",
            owner=cfg.current_user,
            assignee=assignee,
            watchers=[],
            status="active",
            slug_override=slug_override,
            description=_retire_body(ref.id_slug),
            created_by="retire",
        )
    except (ConfigError, ValueError) as exc:
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


def _cleanup_branch(cfg: Config, ref: TaskRef) -> None:
    """Delete the retiring ticket's git branch, best-effort.

    Reads the `## Dev` blackboard section (still present pre-retro) and hands it
    to `branchcleanup.delete_ticket_branch`. Any failure — `git`/`gh` missing, a
    read error, git not enabled — is reported and swallowed: branch hygiene is a
    courtesy on top of retire, not a precondition for it.
    """
    if not cfg.git_enabled:
        return
    try:
        root = git._toplevel(ref.ticket_path)
        if root is None:
            return
        blackboard = read_blackboard(ref.ticket_path, blackboard_required=False)
    except (GitError, OSError, TaskFileError) as exc:
        typer.echo(f"Retire: branch cleanup skipped ({exc}).")
        return
    try:
        delete_ticket_branch(cfg, root, blackboard, echo=typer.echo)
    except Exception as exc:  # noqa: BLE001 — never let cleanup abort retire
        typer.echo(f"Retire: branch cleanup failed ({exc}).")


def _default_agent(cfg: Config) -> str:
    default = cfg.default_agent()
    if default is None:
        raise ConfigError(
            "No agent types declared in [agents]. Pass --agent or declare "
            "at least one `[agents.*]` table in coga.toml."
        )
    return default.name


def _retire_body(target_slug: str) -> str:
    template = files("coga.resources").joinpath("retire.md").read_text()
    return template.format(slug=target_slug).strip()


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
