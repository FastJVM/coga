"""`relay mv <slug> (--group <name> | --ungroup)` — relocate a task between
top-level and a one-level group directory.

The companion to `relay draft --group`: that groups a task at creation, this
regroups one after the fact. The move is a directory relocation only — a
task's slug is its leaf directory name and nothing in the ticket stores its
path — so the body is never touched. The rename lands through the normal git
sync layer, like every other state mutation.
"""

from __future__ import annotations

import re
import shutil
import sys

import typer

from relay import git
from relay.config import ConfigError, load_config
from relay.paths import tasks_dir
from relay.tasks import TaskNotFoundError, read_ticket, resolve_task

_GROUP_RE = re.compile(r"[a-z0-9][a-z0-9-]*$")


def mv(
    task: str = typer.Argument(..., help="Task ID or id-slug (bare or group-qualified)."),
    group: str | None = typer.Option(
        None,
        "--group",
        help="Destination group: move the task into tasks/<group>/<slug>/.",
    ),
    ungroup: bool = typer.Option(
        False,
        "--ungroup",
        help="Move the task out of its group, back to top-level tasks/<slug>/.",
    ),
) -> None:
    """Move a task into a group directory, or back out to top-level."""
    if group is not None and ungroup:
        _bail("Pass either --group <name> or --ungroup, not both.")
    if group is None and not ungroup:
        _bail("Pass a destination: --group <name> or --ungroup.")

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        _bail(str(exc))

    # A live agent session writes into the task dir; moving it out from under
    # an in-progress run would strand the session and its lock. Make the user
    # pause first rather than silently breaking a running task.
    ticket = read_ticket(ref)
    if ticket.status == "in_progress":
        _bail(
            f"{ref.id_slug} is in_progress — pause it (`relay mark paused "
            f"{ref.id_slug}`) before moving, so no running session loses its "
            "directory."
        )

    dest_group = None if ungroup else _validate_group(cfg, group)
    if dest_group == ref.group:
        where = "already top-level" if dest_group is None else f"already in group {dest_group!r}"
        _bail(f"{ref.id_slug} is {where} — nothing to move.")

    parent = tasks_dir(cfg) / dest_group if dest_group else tasks_dir(cfg)
    dest_path = parent / ref.slug
    if dest_path.exists():
        _bail(
            f"Destination already exists: {dest_path}. A task with leaf "
            f"{ref.slug!r} is already there — rename one first."
        )

    old_path = ref.path
    old_id = ref.id_slug
    new_id = f"{dest_group}/{ref.slug}" if dest_group else ref.slug

    parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old_path), str(dest_path))

    typer.echo(f"Moved {old_id} → {new_id}")
    if dest_group is not None:
        typer.echo(f"  Reference it as `{new_id}` (group-qualified) from now on.")

    # Stage both the vanished source and the new destination so git records a
    # rename. Anchor on the destination (the task dir still exists there) for
    # git-root resolution, so a sync failure logs to the moved task's own
    # log.md rather than a stray file under tasks/.
    git.sync_paths(
        cfg,
        dest_path,
        [old_path, dest_path],
        message=f"Ticket: {old_id} → {new_id} — moved",
    )


def _validate_group(cfg, group: str) -> str:
    """Validate a destination group name. Mirrors the create-time check.

    A group is a single directory under `tasks/` with no `ticket.md` of its
    own. Reject names that would nest, don't match the task-slug shape, or
    collide with an existing top-level task (a task name can't double as a
    group).
    """
    group = group.strip()
    if not group:
        _bail("group name cannot be empty")
    if "/" in group:
        _bail(
            f"group {group!r} cannot contain '/': task groups don't nest "
            "(one level under tasks/ only)."
        )
    if not _GROUP_RE.fullmatch(group):
        _bail(
            f"group {group!r} must be a slug (lowercase letters, digits, "
            "hyphens; starting alphanumeric)."
        )
    if (tasks_dir(cfg) / group / "ticket.md").is_file():
        _bail(
            f"{tasks_dir(cfg) / group} is an existing top-level task, not a "
            "group — pick a different group name."
        )
    return group


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
