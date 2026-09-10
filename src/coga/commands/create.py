"""Raw draft-ticket creating for `coga create`.

Leaves the new ticket as `draft`. Does not post to Slack and does not launch
an agent. For guided authoring use `coga ticket`; to start work, mark the
ticket active and then launch it.

The positional reads like the task ref it becomes: a `/` separates an optional
sub-directory path from the title leaf, so `coga create "v2/Build the flow"`
lands the ticket at `tasks/v2/build-the-flow` (referenced as
`v2/build-the-flow`), and `marketing/social/relaunch` nests deeper. No slash
means a top-level create.

`--workflow` is optional: a workflow-less draft is a valid authoring
intermediate, it just can't be activated. `coga mark active` refuses a
ticket with no workflow (workflow-less tickets can never be `coga bump`ed),
so add a `workflow:` before activating, or pass `--workflow` up front.

`--description` and `--owner` are optional too, so one command can scaffold a
described, correctly-owned draft. `--description` fills the ticket's
`## Description` section; `--owner` sets `owner:` to a coga name instead of
the local `user` (and, through `create_task`, seeds `human:` and a
workflow-less `assignee:`). A description carrying a level-2 heading line or
the blackboard fence line is refused before anything is written, since either
would break the ticket's section/fence structure.
"""

from __future__ import annotations

import re
import sys

import typer

from coga import git
from coga.config import ConfigError, load_config
from coga.create import create_task
from coga.taskfile import BLACKBOARD_FENCE, fence_count
from coga.validate import TaskValidationError

# The line shape compose reads as a body section heading (`_SECTION_HEADING_RE`
# in compose.py): `##` then whitespace. A bare `##` line counts too, because
# `\s+` there also matches the newline. `###` and deeper stay inside a section.
_SECTION_HEADING_LINE_RE = re.compile(r"^##(?:\s|$)", re.MULTILINE)


def create(
    title: str = typer.Argument(
        ...,
        help=(
            "Title for the new ticket. Prefix with a sub-directory path to "
            "place it there: 'v2/Build the flow' lands at tasks/v2/, "
            "'marketing/social/relaunch' nests deeper. No slash = top level."
        ),
    ),
    workflow: str | None = typer.Option(
        None,
        "--workflow",
        help=(
            "Workflow name (path under coga/workflows/) to attach. "
            "Optional, but a workflow-less draft can't be activated until "
            "one is added."
        ),
    ),
    description: str | None = typer.Option(
        None,
        "--description",
        help=(
            "Short text for the new ticket's '## Description' section. May "
            "not contain a '## ' heading line or the blackboard fence line."
        ),
    ),
    owner: str | None = typer.Option(
        None,
        "--owner",
        help=(
            "Coga name to own the ticket (also seeds human:). Defaults to "
            "`user` from coga.local.toml."
        ),
    ),
) -> None:
    """Create a new raw draft ticket."""
    create_draft(
        title=title,
        workflow=workflow,
        description=description,
        owner=owner,
    )


def create_draft(
    *,
    title: str,
    workflow: str | None = None,
    description: str | None = None,
    owner: str | None = None,
) -> dict[str, object]:
    """Create a raw draft ticket from a (possibly path-qualified) title.

    Does not post to Slack — it just writes the ticket and git-syncs it.

    The `title` is split on `/` into an optional sub-directory path and the
    title leaf (see `_split_create_path`), so `"v2/Build the flow"` drafts the
    ticket at `tasks/v2/build-the-flow`. This is shared by `coga create` and
    `coga ticket`'s new-draft branch, so both place tickets the same way.

    `workflow` is optional. A workflow-less draft is a valid authoring
    intermediate — `coga mark active` is the gate that refuses to activate
    a ticket with no workflow, since a workflow-less ticket can never be
    `coga bump`ed.

    `description` (optional) becomes the `## Description` text; `None` or empty
    leaves the section blank. `owner` (optional) is stripped and must not be
    empty; `None` keeps the local `user`. Both are checked before anything is
    written, so a rejected create leaves nothing on disk.
    """
    directory, leaf_title = _split_create_path(title)
    if not leaf_title.strip():
        _bail("title cannot be empty")
    if owner is not None:
        owner = owner.strip()
        if not owner:
            _bail("owner cannot be empty")
    if description:
        problem = _description_structure_problem(description)
        if problem:
            _bail(problem)

    try:
        cfg = load_config()
    except ConfigError as exc:
        _bail(str(exc))

    try:
        result = create_task(
            cfg=cfg,
            title=leaf_title,
            workflow_name=workflow,
            contexts=[],
            owner=owner or cfg.current_user,
            assignee=None,
            watchers=[],
            status="draft",
            directory=directory,
            description=description,
        )
    except (TaskValidationError, ValueError) as exc:
        _bail(str(exc))

    slug = result["slug"]
    typer.echo(f"{slug}: created (draft)")
    git.sync_task_state(cfg, result["path"], message=f"Ticket: {slug} — created")
    return result


def _description_structure_problem(description: str) -> str | None:
    """Why `description` would break the ticket's structure, or None.

    The description is written verbatim under `## Description`. A level-2
    heading line would end that section early (compose would read the rest as
    another section), and a blackboard fence on its own line would split the
    body from the blackboard — `split_body` then sees two fences. An inline
    mention of the fence string is harmless and allowed, as are `###`
    subheadings.
    """
    if _SECTION_HEADING_LINE_RE.search(description):
        return (
            "description cannot contain a level-2 heading line ('## ...'): "
            "it would split the ticket's '## Description' section. Use '###' "
            "or deeper, or edit the ticket body after create."
        )
    if fence_count(description):
        return (
            f"description cannot contain the blackboard fence line "
            f"({BLACKBOARD_FENCE!r}): it would split the ticket body from its "
            "blackboard."
        )
    return None


def _split_create_path(positional: str) -> tuple[str | None, str]:
    """Split a `coga create` positional into (sub-directory, title).

    A `/` separates an optional sub-directory path from the title leaf, so the
    positional reads like the task ref it becomes: `v2/Build the flow` →
    ("v2", "Build the flow"), `marketing/social/relaunch` →
    ("marketing/social", "relaunch"). No slash means a top-level create. The
    leaf is the human title (create slugifies it for the slug); the prefix is
    the sub-directory under tasks/, validated downstream in `create_task`.
    """
    head, sep, leaf = positional.rpartition("/")
    if not sep:
        return None, positional
    directory = head.strip().strip("/")
    return (directory or None), leaf


def _bail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    sys.exit(2)
