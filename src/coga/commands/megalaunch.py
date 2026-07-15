"""`coga megalaunch` — sequentially attempt launchable work.

Three ways in, one engine:

- bare `coga megalaunch` — sweep every launchable `active` task.
- `coga megalaunch --pick` — interactive picker over the operator's `active`
  + `in_progress` agent tickets, all pre-checked; the confirmed set runs as
  an explicit selection (and is saved for `--relaunch`).
- `coga megalaunch --relaunch` — replay the last confirmed selection.
"""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from coga import notification
from coga.commands.launch import _interactive_stdio_has_tty
from coga.config import Config, ConfigError, load_config
from coga.megalaunch import (
    MegalaunchError,
    MegalaunchRun,
    launchable_candidates,
    load_selection,
    render_run_summary,
    run_megalaunch,
    save_selection,
)
from coga.tasks import TaskRef, UnknownDirectoryError, list_tasks
from coga.ticket import Ticket


def megalaunch(
    directory: str | None = typer.Argument(
        None,
        metavar="[DIR]",
        help=(
            "Only sweep (or pick from) tasks under `tasks/<DIR>/` (a "
            "directory path, nested ones included, e.g. `marketing` or "
            "`marketing/social`), same as `coga status <DIR>`. Omit to "
            "cover every task."
        ),
    ),
    pick: bool = typer.Option(
        False,
        "--pick",
        help=(
            "Choose interactively: a pre-checked list of your active and "
            "in_progress tickets; the confirmed set launches and is saved "
            "for --relaunch."
        ),
    ),
    relaunch: bool = typer.Option(
        False,
        "--relaunch",
        help="Re-run the last confirmed picker selection.",
    ),
    max_tasks: int | None = typer.Option(
        None,
        "--max-tasks",
        min=1,
        help="Stop after this many launchable tasks have been attempted.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="Only drain tasks currently assigned to this configured agent type.",
    ),
) -> None:
    """Run the shared megalaunch engine once."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    if agent is not None:
        try:
            cfg.agent_type(agent)
        except ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            sys.exit(2)

    try:
        selection = _resolve_selection(
            cfg, directory, pick=pick, relaunch=relaunch, agent=agent
        )
    except (MegalaunchError, UnknownDirectoryError, ConfigError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    if selection is not None and not selection:
        # The picker (or an empty candidate list) already said why.
        return

    try:
        run = run_megalaunch(
            cfg,
            max_tasks=max_tasks,
            agent_filter=agent,
            directory=directory,
            selection=selection,
        )
    except (MegalaunchError, UnknownDirectoryError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    # Local outcome to stdout before the notification post, so a Slack crash
    # still leaves the run summary visible (coga/sync convention).
    typer.echo(render_run_summary(run))
    message = _drain_post_text(run)
    if message is not None:
        notification.post(cfg, message)
    if run.counts["failed"]:
        sys.exit(1)


def _resolve_selection(
    cfg: Config,
    directory: str | None,
    *,
    pick: bool,
    relaunch: bool,
    agent: str | None,
) -> list[str] | None:
    """Turn the flags into the engine's `selection`.

    `None` means the non-explicit sweep; an empty list means the human
    confirmed nothing (caller reports and exits cleanly).
    """
    if relaunch and (pick or directory is not None):
        raise MegalaunchError(
            "--relaunch replays the last saved selection; combining it with "
            "--pick or a directory is ambiguous."
        )

    if relaunch:
        return _saved_selection_still_on_disk(cfg)
    if not pick:
        # Default: the non-interactive sweep of launchable active tasks.
        return None

    # --pick: the interactive picker over an explicit, pre-checked list.
    if not _interactive_stdio_has_tty():
        raise MegalaunchError(
            "The megalaunch picker is interactive and requires a TTY. "
            "Drop --pick for the non-interactive sweep."
        )
    candidates = launchable_candidates(cfg, directory=directory, agent_filter=agent)
    if not candidates:
        typer.echo("No launchable tasks (active or in_progress, agent-assigned).")
        return []
    selection = _pick_selection(candidates)
    if selection:
        save_selection(cfg, selection)
    else:
        typer.echo("Nothing selected — nothing launched.")
    return selection


def _saved_selection_still_on_disk(cfg: Config) -> list[str]:
    """The saved selection minus tasks that no longer exist, reported loudly."""
    saved = load_selection(cfg)
    existing = {ref.id_slug for ref in list_tasks(cfg)}
    kept = [slug for slug in saved if slug in existing]
    for slug in saved:
        if slug not in existing:
            typer.secho(
                f"Saved selection: {slug} no longer exists — skipped.",
                fg=typer.colors.YELLOW,
                err=True,
            )
    if not kept:
        raise MegalaunchError(
            "None of the saved selection's tasks exist anymore — run the "
            "picker again."
        )
    return kept


def parse_toggle_tokens(line: str, count: int) -> set[int] | None:
    """Parse a toggle line ('3', '1 3', '2,4') into zero-based indices.

    Returns None on any token that isn't a number in [1, count] — the caller
    re-prompts instead of guessing.
    """
    indices: set[int] = set()
    for token in line.replace(",", " ").split():
        if not token.isdigit():
            return None
        number = int(token)
        if not 1 <= number <= count:
            return None
        indices.add(number - 1)
    return indices


def _pick_selection(candidates: list[tuple[TaskRef, Ticket]]) -> list[str]:
    """Numbered toggle picker: everything pre-checked, Enter launches.

    Returns the confirmed slugs, or an empty list when the human backed out
    (`q`, or confirming with nothing checked).
    """
    console = Console()
    selected = set(range(len(candidates)))
    while True:
        console.print(_picker_table(candidates, selected))
        line = (
            typer.prompt(
                "Toggle (e.g. '3' or '1 3'), 'all'/'none', Enter to launch, "
                "q to quit",
                default="",
                show_default=False,
            )
            .strip()
            .lower()
        )
        if line == "q":
            return []
        if line == "":
            return [candidates[i][0].id_slug for i in sorted(selected)]
        if line == "all":
            selected = set(range(len(candidates)))
            continue
        if line == "none":
            selected = set()
            continue
        toggles = parse_toggle_tokens(line, len(candidates))
        if toggles is None:
            typer.secho(
                f"Enter numbers 1-{len(candidates)}, 'all', 'none', or q.",
                fg=typer.colors.YELLOW,
            )
            continue
        selected ^= toggles


def _picker_table(
    candidates: list[tuple[TaskRef, Ticket]], selected: set[int]
) -> Table:
    table = Table(show_lines=False, show_edge=False, pad_edge=False)
    table.add_column("#", justify="right")
    table.add_column("sel")
    table.add_column("slug")
    table.add_column("status")
    table.add_column("step")
    table.add_column("title")
    for index, (ref, ticket) in enumerate(candidates):
        table.add_row(
            str(index + 1),
            # Text, not str: a bare "[x]" would be eaten as Rich markup.
            Text("[x]" if index in selected else "[ ]"),
            ref.id_slug,
            ticket.status,
            ticket.step or "-",
            ticket.title,
        )
    return table


def _drain_post_text(run: MegalaunchRun) -> str | None:
    """One live line: what was drained, or that budget skipped everything.

    Silent when the run had no results at all — an empty repo is lifecycle
    noise, not an outcome a teammate needs within minutes.
    """
    if not run.results:
        return None
    counts = run.counts
    launched = [result.slug for result in run.results if result.launched]
    parts = [
        "launched " + ", ".join(f"*{slug}*" for slug in launched)
        if launched
        else "nothing launched"
    ]
    if counts["skipped-budget"]:
        parts.append(f"{counts['skipped-budget']} skipped for budget")
    not_launchable = (
        counts["skipped-unresolved-blocker"]
        + counts["skipped-human-gate"]
        + counts["skipped-unlaunchable"]
    )
    if not_launchable:
        parts.append(f"{not_launchable} not launchable")
    if counts["failed"]:
        parts.append(f"{counts['failed']} failed")
    scope = [s for s in (run.agent_filter, run.directory) if s is not None]
    if run.selection is not None:
        scope.append("selected")
    label = f"Megalaunch drain ({', '.join(scope)})" if scope else "Megalaunch drain"
    return label + ": " + "; ".join(parts)
