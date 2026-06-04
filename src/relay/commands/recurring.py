"""`relay recurring` — scan recurring templates and launch what's due."""

from __future__ import annotations

import os
import sys
from datetime import datetime

import typer

from relay import git
from relay.config import ConfigError, load_config
from relay.recurring import (
    DueScan,
    RecurringError,
    scaffold_named,
    scan_debug,
    scan_due,
)
from relay.slack import notify
from relay.tasks import TaskRef, read_ticket

# Idle-timeout backstop (seconds) armed for the `--all` debug sweep. That path
# force-launches interactive REPLs with no workflow driving them to a done
# signal, so a stalled or crashed agent would otherwise block the sequential
# sweep forever — the hang this command was seen to hit. Generous enough that a
# slow-but-progressing agent (which streams PTY output) never trips it; only a
# genuinely silent REPL does. Overridable via the `RELAY_REPL_IDLE_TIMEOUT`
# env var, which `relay launch` reads.
_DEBUG_REPL_IDLE_TIMEOUT = "900"

app = typer.Typer(
    name="recurring",
    help="Scan recurring task templates and launch any that are due.",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Launch every due task in interactive mode for this run, even "
        "ones whose ticket says `mode: auto`. For debugging; ticket files "
        "are not modified.",
    ),
    all_: bool = typer.Option(
        False,
        "--all",
        help="Debug: ignore the schedule and status filter — scaffold a fresh "
        "throwaway run of EVERY template and launch them all, regardless of "
        "whether this period already ran. Real period tasks are left "
        "untouched; the debug runs are yours to `relay delete` afterward.",
    ),
) -> None:
    """Scan every recurring template and launch any due tasks, sequentially.

    Bare `relay recurring` is the default action. For each template under
    `relay-os/recurring/` it get-or-creates the current period's task, then
    launches every one still `active` — most-overdue first, one at a time.
    Current period only: running this once a month for a weekly template
    produces one run, not a backlog. It does not install or manage system
    cron; nothing runs unless you invoke it.

    `--all` is the debug escape hatch: it scaffolds a fresh, isolated
    throwaway run of every template and launches them all, bypassing both the
    schedule and the "already ran this period" skip. Use it to exercise the
    launch path without waiting for a schedule or disturbing real period state.

    `relay recurring launch <name>` force-runs one named template now.
    """
    if ctx.invoked_subcommand is not None:
        return

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    if all_:
        _launch_all_debug(cfg)
        return

    scan = scan_due(cfg, allow_interactive=_interactive_stdio_has_tty())
    _broadcast_scan(cfg, scan)
    _print_table(scan)

    due = scan.due
    if not due:
        typer.echo("No recurring tasks due.")
        return

    mode_override = "interactive" if interactive else None
    typer.echo(f"\nLaunching {len(due)} due task(s) sequentially...\n")
    from relay.commands.launch import launch as launch_cmd

    for i, task in enumerate(due, 1):
        typer.secho(
            f"[{i}/{len(due)}] {task.ref.id_slug}", fg=typer.colors.CYAN, bold=True
        )
        # Sequential by design: each launch blocks until the agent session
        # exits before the next begins. `scan_due` filters launches that
        # cannot run in the current stdio context, so every task here should
        # be spawnable.
        launch_cmd(
            task.ref.slug,
            agent_override=None,
            prompt_report=False,
            no_verify=False,
            mode_override=mode_override,
        )
        _stop_if_unfinished_after_launch(task.ref, interactive=interactive)


def _launch_all_debug(cfg) -> None:
    """Scaffold and launch a fresh throwaway run of every template (`--all`).

    Debug-only. Unlike the bare sweep this does not broadcast to Slack or
    commit task state — the runs are disposable scratch tasks, not real
    recurring work — and it never bails on an unfinished run (the human is
    driving). Script templates run as scripts; everything else launches
    interactively so there is a live console to watch.
    """
    scan = scan_debug(cfg, allow_interactive=_interactive_stdio_has_tty())
    _print_table(scan)
    for name, msg in scan.errors:
        typer.secho(f"  skipped {name}: {msg}", fg=typer.colors.YELLOW, err=True)

    runs = scan.tasks
    if not runs:
        typer.echo("No recurring templates to launch.")
        return

    for task in runs:
        typer.echo(f"Created {task.ref.id_slug} (debug)")

    typer.echo(f"\nLaunching {len(runs)} debug run(s) sequentially...\n")
    from relay.commands.launch import launch as launch_cmd

    # Arm the supervisor idle-timeout so one stuck interactive REPL can't block
    # the rest of the sweep (see `_DEBUG_REPL_IDLE_TIMEOUT`). `setdefault` lets
    # an operator override the window without losing the backstop.
    os.environ.setdefault("RELAY_REPL_IDLE_TIMEOUT", _DEBUG_REPL_IDLE_TIMEOUT)

    for i, task in enumerate(runs, 1):
        typer.secho(
            f"[{i}/{len(runs)}] {task.ref.id_slug}", fg=typer.colors.CYAN, bold=True
        )
        ticket = read_ticket(task.ref)
        # Force interactive so there's a live console — except script tickets,
        # which compose no agent prompt and reject a mode override.
        mode_override = None if ticket.mode == "script" else "interactive"
        launch_cmd(
            task.ref.slug,
            agent_override=None,
            prompt_report=False,
            no_verify=False,
            mode_override=mode_override,
        )

    slugs = " ".join(t.ref.slug for t in runs)
    typer.secho(
        f"\nDebug runs left on disk. Clean up with: relay delete {slugs}",
        fg=typer.colors.BRIGHT_BLACK,
    )


@app.command("launch")
def launch(
    name: str = typer.Argument(
        ...,
        help="Recurring task name — the directory under relay-os/recurring/.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Launch in interactive mode even if the template says "
        "`mode: auto`. For debugging; the ticket file is not modified.",
    ),
) -> None:
    """Scaffold a named recurring template now and launch it.

    Ignores the template's schedule — the on-demand entry point behind
    aliases like `relay dream`. The task slug still uses the schedule-derived
    period key, so this and a bare `relay recurring` converge on one task
    directory per period: a second `launch` in the same period reuses the
    existing task instead of creating a duplicate.
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        outcome = scaffold_named(cfg, name)
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    ref = outcome.ref
    if outcome.created:
        ticket = read_ticket(ref)
        typer.echo(f"Created {ref.id_slug}")
        notify(
            cfg,
            f"🔁 recurring scaffolded *{ref.id_slug}* "
            f"\"{ticket.title}\" in {cfg.project_name} — "
            f"assignee {ticket.assignee or 'unassigned'}",
            kind="recurring",
            detail=f"recurring scaffolded \"{ticket.title}\" — "
            f"assignee {ticket.assignee or 'unassigned'}",
            ticket=ref.id_slug,
            owner=ticket.owner,
            task_path=ref.path,
        )
        git.sync_task_state(
            cfg, ref.path, message=f"Ticket: {ref.id_slug} — recurring scaffold"
        )
    else:
        typer.echo(f"{ref.id_slug} already scaffolded for this period")

    _launch_scaffolded(ref, mode_override="interactive" if interactive else None)


def _launch_scaffolded(ref: TaskRef, *, mode_override: str | None = None) -> None:
    """Launch a freshly scaffolded recurring task.

    Recurring tasks scaffold straight to `active` — they are machine-authored
    ready jobs, so there is no separate activation step. A task already past
    `active` (a finished or paused run, e.g. re-running `relay dream` mid-week)
    is left alone — re-launching it would be wrong, and saying so beats
    silently doing nothing.
    """
    ticket = read_ticket(ref)
    if ticket.status != "active":
        typer.secho(
            f"{ref.id_slug} is {ticket.status}; not launching.",
            fg=typer.colors.YELLOW,
        )
        return

    typer.echo(f"Launching {ref.id_slug}")
    from relay.commands.launch import launch as launch_cmd

    launch_cmd(
        ref.slug,
        agent_override=None,
        prompt_report=False,
        no_verify=False,
        mode_override=mode_override,
    )


def _stop_if_unfinished_after_launch(ref: TaskRef, *, interactive: bool) -> None:
    """Stop a bare recurring sweep if one launched task is still in flight.

    `interactive` is set when the sweep is `--interactive` (or the just-
    launched template's own `mode:` was interactive). In that case the human
    is driving — exiting the agent without marking done is a valid "move on"
    signal, not a stuck task — so we print a note and continue instead of
    bailing the sweep.
    """
    if not (ref.path / "ticket.md").exists():
        return

    ticket = read_ticket(ref)
    if ticket.status == "done":
        return

    if interactive or ticket.mode == "interactive":
        typer.secho(
            f"{ref.id_slug}: ended with status={ticket.status!r}; "
            "continuing to next due task (interactive).",
            fg=typer.colors.YELLOW,
        )
        return

    typer.secho(
        f"{ref.id_slug}: recurring launch returned with status={ticket.status!r}; "
        "stopping before the next due task. Finish or delete this run, then "
        "rerun `relay recurring`.",
        fg=typer.colors.RED,
        err=True,
    )
    sys.exit(1)


# --- scan reporting -----------------------------------------------------------


def _interactive_stdio_has_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _broadcast_scan(cfg, scan: DueScan) -> None:
    """Post Slack lines for newly scaffolded tasks and skipped templates."""
    for task in scan.tasks:
        if not task.created:
            continue
        ticket = read_ticket(task.ref)
        typer.echo(f"Created {task.ref.id_slug}")
        notify(
            cfg,
            f"🔁 recurring scaffolded *{task.ref.id_slug}* "
            f"\"{ticket.title}\" in {cfg.project_name} — "
            f"assignee {ticket.assignee or 'unassigned'}",
            kind="recurring",
            detail=f"recurring scaffolded \"{ticket.title}\" — "
            f"assignee {ticket.assignee or 'unassigned'}",
            ticket=task.ref.id_slug,
            owner=ticket.owner,
            task_path=task.ref.path,
        )
        git.sync_task_state(
            cfg,
            task.ref.path,
            message=f"Ticket: {task.ref.id_slug} — recurring scaffold",
        )

    if scan.errors:
        n = len(scan.errors)
        plural = "" if n == 1 else "s"
        bullets = "\n".join(f"• {name}: {msg}" for name, msg in scan.errors)
        inline = "; ".join(f"{name} ({msg})" for name, msg in scan.errors)
        notify(
            cfg,
            f"⚠️ recurring scan skipped {n} template{plural}\n{bullets}",
            kind="recurring-error",
            detail=f"⚠️ recurring scan skipped {n} template{plural}: {inline}",
        )


def _print_table(scan: DueScan) -> None:
    """Print a one-line-per-template scan summary."""
    if not scan.tasks and not scan.errors:
        return

    now = datetime.now()
    typer.echo(f"Recurring scan — {now:%Y-%m-%d %H:%M}\n")
    for task in scan.tasks:
        when = _firing_label(task.last_fire, now)
        if task.ref is None:
            # The period was scaffolded earlier this cycle and the task
            # was removed afterwards (Dream self-delete or `relay delete`).
            action = typer.style(
                "skip (ran this period)", fg=typer.colors.BRIGHT_BLACK
            )
        elif task.launchable:
            action = typer.style("→ launch", fg=typer.colors.GREEN)
        else:
            action = typer.style(
                f"skip ({task.status})", fg=typer.colors.BRIGHT_BLACK
            )
        typer.echo(f"  {task.template:<20} {when:<26} {action}")

    for name, msg in scan.errors:
        bad = typer.style(f"skip (error: {msg})", fg=typer.colors.RED)
        typer.echo(f"  {name:<20} {'':<26} {bad}")


def _firing_label(last_fire: datetime, now: datetime) -> str:
    """Human label for a scheduled firing — 'ready' or 'overdue Nd'."""
    delta = now - last_fire
    stamp = last_fire.strftime("%a %H:%M")
    if delta.total_seconds() < 86400:
        return f"ready ({stamp})"
    return f"overdue {delta.days}d ({stamp})"
