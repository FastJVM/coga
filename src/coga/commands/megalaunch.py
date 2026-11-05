"""`coga megalaunch` — sequentially attempt launchable work.

Three ways in, one engine:

- bare `coga megalaunch` — sweep every launchable `active` or `in_progress`
  task (`active` starts, `in_progress` resumes), then fixed-point drain blocked
  tasks whose named dependency finished during the run.
- `coga megalaunch --pick` — arrow-key picker over every non-terminal task
  (any owner, any status except done/canceled — no launchability pre-filter),
  nothing pre-checked;
  the confirmed set runs staged — prepare (a batch prompt offers to author
  picked drafts) → check → launch, each pick activated as its own launch
  starts — as an explicit selection (and is saved for `--relaunch`).
- `coga megalaunch --relaunch` — replay the last confirmed selection.
"""

from __future__ import annotations

import sys

import typer

from coga import git, notification
from coga.launch import _interactive_stdio_has_tty
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
from coga.picker import PickerColumn, PickerRow, pick
from coga.tasks import TaskRef, UnknownDirectoryError, list_tasks, read_ticket
from coga.ticket import Ticket, TicketError


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
            "Choose interactively: an arrow-key list of every non-terminal "
            "task (any owner, any status except done/canceled), "
            "nothing pre-checked; the confirmed set is prepared (a batch "
            "prompt offers to run the authoring interview on picked drafts), "
            "checked, then launched — each pick is activated as its own launch "
            "starts — and is saved for --relaunch."
            " Selection filters the service-ordered queue; the order tasks "
            "are picked does not set their run order."
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
        help=(
            "Stop after this many launch attempts; dependency-drain retries "
            "count against the same budget."
        ),
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help=(
            "Use this configured agent type for picked-draft authoring and "
            "the first launched step (ephemeral; human-assigned working "
            "steps still skip, unlike an explicit `coga launch --agent` "
            "assist)."
        ),
    ),
) -> None:
    """Drain launchable tasks sequentially.

    Tasks drain oldest-first by their first `coga/log.md` entry. Naming tasks
    in a sub-directory with numeric prefixes such as `1-`, `2-`, `3-`
    sequences that directory as one contiguous block in number order; this is
    a naming convention, not a flag.
    """
    from coga.launch import LaunchBail, require_agent_sessions

    try:
        require_agent_sessions()
    except LaunchBail as exc:
        typer.secho(exc.reason, fg=typer.colors.RED, err=True)
        raise typer.Exit(exc.code) from None
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

    # Pick and queue from control's state, not a stale local copy: every
    # later read (picker list, sweep queue, saved selection) sees these files.
    # A feature/detached checkout only fetches; Git-off, non-Git and no-remote
    # repos skip. `False` means control could not be brought level, and
    # refresh already said why on stderr.
    if not git.refresh(cfg):
        typer.secho(
            "megalaunch: could not bring this checkout level with control; "
            "nothing was picked or launched.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(1)
    try:
        cfg = load_config(cfg.repo_root)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        selection = _resolve_selection(cfg, directory, pick=pick, relaunch=relaunch)
    except (MegalaunchError, UnknownDirectoryError, ConfigError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)
    if selection is not None and not selection:
        # The picker (or an empty candidate list) already said why.
        return

    # A picked selection that includes drafts gets one batch question: run the
    # guided authoring interview on them first, or launch what's ready and let
    # the not-ready drafts report themselves. Only asked when there's a draft
    # to author, so a pick of ready work is never interrupted.
    author_drafts = _confirm_author_drafts(cfg, selection) if selection else False

    try:
        run = run_megalaunch(
            cfg,
            max_tasks=max_tasks,
            agent_override=agent,
            directory=directory,
            selection=selection,
            author_drafts=author_drafts,
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


def _confirm_author_drafts(cfg: Config, selection: list[str]) -> bool:
    """Ask once whether to author the picked drafts, or `False` if none.

    A picked `draft` is not-yet-ready work: authoring it (the guided
    `coga ticket` interview) is what makes it launchable. But forcing an
    interview on every pick is heavy, so this is a single opt-in prompt raised
    only when the confirmed selection actually contains a draft — a pick of
    ready work is never interrupted.
    """
    wanted = set(selection)
    drafts = [
        ref.id_slug
        for ref in list_tasks(cfg)
        if ref.id_slug in wanted and _is_draft(ref)
    ]
    if not drafts:
        return False
    noun = "draft" if len(drafts) == 1 else "drafts"
    return typer.confirm(
        f"{len(drafts)} picked {noun} ({', '.join(sorted(drafts))}) — run the "
        "guided authoring interview to make them ready before launching?",
        default=True,
    )


def _is_draft(ref: TaskRef) -> bool:
    try:
        return read_ticket(ref).status == "draft"
    except TicketError:
        return False


def _resolve_selection(
    cfg: Config,
    directory: str | None,
    *,
    pick: bool,
    relaunch: bool,
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

    # --pick: the interactive arrow-key picker over an explicit list.
    if not _interactive_stdio_has_tty():
        raise MegalaunchError(
            "The megalaunch picker is interactive and requires a TTY. "
            "Drop --pick for the non-interactive sweep."
        )
    candidates = launchable_candidates(cfg, directory=directory)
    if not candidates:
        typer.echo("No tasks to pick (only done/canceled tasks exist).")
        return []
    selection = _pick_selection(candidates)
    if selection:
        save_selection(cfg, selection)
        typer.echo(f"Picked: {', '.join(selection)}")
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


def _pick_selection(candidates: list[tuple[TaskRef, Ticket]]) -> list[str]:
    """Arrow-key picker: ↑/↓ (or j/k) move, Space toggles, Enter launches.

    Nothing starts checked — the list reaches wide (other owners' tickets,
    drafts, paused, blocked), so every launch is an explicit opt-in. Returns
    the confirmed slugs, or an empty list when the human backed out (`q`/Esc,
    Ctrl-C, or confirming with nothing checked).
    """
    rows = [
        PickerRow(
            key=ref.id_slug,
            cells=(
                ref.id_slug,
                ticket.status,
                ticket.owner or "-",
                ticket.step or "-",
                ticket.title,
            ),
        )
        for ref, ticket in candidates
    ]
    columns = (
        PickerColumn("slug", ratio=2),
        PickerColumn("status"),
        PickerColumn("owner", ratio=1),
        PickerColumn("step", ratio=1),
        PickerColumn("title", ratio=3),
    )
    try:
        chosen = pick(
            rows,
            columns,
            hint="↑/↓ move · Space toggle · a all · n none · Enter launch · q quit",
        )
    except KeyboardInterrupt:
        # Ctrl-C used to decode as "quit" alongside `q`, and quitting here
        # launches nothing — so folding both into [] keeps megalaunch's
        # behaviour byte-for-byte. `coga init` cannot do the same: there, a
        # confirmed-empty answer writes a coga.toml, so it lets this propagate.
        return []
    return chosen if chosen is not None else []


def _drain_post_text(run: MegalaunchRun) -> str | None:
    """One live line: what was drained.

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
    not_launchable = (
        counts["skipped-unresolved-blocker"]
        + counts["skipped-human-gate"]
        + counts["skipped-unlaunchable"]
    )
    if not_launchable:
        parts.append(f"{not_launchable} not launchable")
    if counts["drained"]:
        parts.append(f"{counts['drained']} dependency-drained")
    if counts["failed"]:
        parts.append(f"{counts['failed']} failed")
    scope = [run.directory] if run.directory is not None else []
    if run.agent_override is not None:
        scope.append(f"as {run.agent_override}")
    if run.selection is not None:
        scope.append("selected")
    label = f"Megalaunch drain ({', '.join(scope)})" if scope else "Megalaunch drain"
    return label + ": " + "; ".join(parts)
