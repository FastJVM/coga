"""The recurring sweep body — extracted from the Typer command head.

`coga recurring` (bare) and `coga recurring launch <name>` are thin heads: the
first sets a small env contract and launches the packaged
`bootstrap/recurring-scan` script target, which calls `run_recurring_scan`; the
second delegates straight to `run_recurring_named`. Both entry points share the
one get-or-create implementation in `coga.recurring` and the one control-branch
sync stack in `coga.recurring_sync`, so neither the bare scan nor the named
launch duplicates create/sync/launch behavior.
"""

from __future__ import annotations

import math
import os
import sys
from datetime import datetime

import typer

from coga.commands.launch import _interactive_stdio_has_tty
from coga.config import Config
from coga.mark import mark_active, mark_paused
from coga.notification import notify
from coga.recurring import (
    DueScan,
    DueTask,
    Template,
    create_named,
    read_last_serviced_period,
    recurring_dir,
    scan_due,
    write_last_serviced_period,
)
from coga.recurring_sync import (
    _append_forced_reused_log,
    _refresh_forced_status_from_control,
    _sync_recurring_create,
    _write_snapshot_from_text,
)
from coga.taskfile import read_blackboard
from coga.tasks import TaskRef, read_ticket
from coga.validate import TaskValidationError

# Default idle-timeout backstop (seconds) the sweep arms on the interactive
# REPLs it spawns: one that stalls or crashes before signalling done would
# otherwise block the sequential sweep forever — the hang this command was seen
# to hit. Generous enough that a slow-but-progressing agent (which streams PTY
# output) never trips it; only a genuinely silent REPL does. `--interactive`
# (a human driving by hand) leaves it off; `COGA_REPL_IDLE_TIMEOUT` overrides
# the window or, at `<= 0` / non-finite, disarms it.
_RECURRING_IDLE_TIMEOUT_SECONDS = 900.0


def run_recurring_scan(cfg: Config, *, force: bool, interactive: bool) -> int:
    """Scan every recurring template and launch any due tasks, sequentially.

    The body behind a bare `coga recurring` (and `coga recurring --all`), moved
    out of the Typer command so the packaged `bootstrap/recurring-scan` script
    target and the deep tests can drive it directly. `force` is the `--all`
    knob; `interactive` is the `--interactive` knob (a human stepping the
    spawned REPLs by hand, so their liveness backstops stay unarmed).

    For each template under `coga/recurring/` it get-or-creates the current
    period's task, then launches every one still `active` or orphaned
    `in_progress` — most-overdue first, one at a time. `done` and `paused` tasks
    are skipped. `--all` forces a real, full run of every template regardless of
    schedule or status.
    """
    scan = scan_due(
        cfg, allow_interactive=_interactive_stdio_has_tty(), force=force
    )
    _broadcast_scan(
        cfg,
        scan,
        respect_handled_period=not force,
        sync_existing=force,
    )
    _print_table(scan, force=force)

    # `--all` force-launches every materialized task regardless of status;
    # the bare sweep launches only the launchable (active/in_progress) ones.
    due = scan.forced if force else scan.due
    if not due:
        typer.echo(
            "No recurring templates to launch." if force else "No recurring tasks due."
        )
        return 0

    # `--interactive` is a human stepping through by hand, so leave the spawned
    # REPL unbounded; an automatic sweep arms the liveness backstops so one stuck
    # agent can't block the tasks behind it.
    idle_timeout = None if interactive else _recurring_idle_timeout(cfg)
    max_session = None if interactive else _recurring_max_session(cfg)
    label = "task(s)" if force else "due task(s)"
    typer.echo(f"\nLaunching {len(due)} {label} sequentially...\n")
    from coga.commands.launch import launch as launch_cmd

    for i, task in enumerate(due, 1):
        typer.secho(
            f"[{i}/{len(due)}] {task.ref.id_slug}", fg=typer.colors.CYAN, bold=True
        )
        if force:
            _prepare_forced_launch(cfg, task)
        # Sequential by design: each launch blocks until the agent session
        # exits before the next begins. `scan_due` filters out templates that
        # cannot run in the current stdio context (`mode: agent` with no TTY), and
        # the liveness backstops release any that launch but then stall. `launch`
        # returns "timeout" when a backstop fired so we record the wedge honestly
        # below instead of pausing it as a human would.
        kind = launch_cmd(
            task.ref.id_slug,
            agent_override=None,
            prompt_report=False,
            idle_timeout=idle_timeout,
            max_session=max_session,
            return_timeout=True,
        )
        _stop_if_unfinished_after_launch(
            cfg, task.ref, interactive=interactive, timed_out=(kind == "timeout")
        )
    return 0


def run_recurring_named(cfg: Config, name: str, *, interactive: bool = False) -> int:
    """Create the named recurring template now and launch it.

    The body behind `coga recurring launch <name>` (and aliases like
    `coga dream`). Ignores the template's schedule — the on-demand entry point.
    The task slug is the stable qualified `recurring/<name>`, so this and a bare
    `coga recurring` converge on one instantiated task directory. Raises
    `RecurringError` (from `create_named`) for the command head to surface.
    """
    outcome = create_named(cfg, name)

    ref = outcome.ref
    if outcome.created:
        created_on_control = _sync_recurring_create(
            cfg, name, ref, respect_handled_period=False
        )
        if not (ref.ticket_path).is_file():
            typer.secho(
                f"{ref.id_slug} was already handled on the control branch; "
                "not launching.",
                fg=typer.colors.BRIGHT_BLACK,
            )
            return 0
        if created_on_control:
            typer.echo(f"Created {ref.id_slug}")
    else:
        typer.echo(f"{ref.id_slug} already created for this period")

    _launch_created(cfg, ref, interactive=interactive)
    return 0


def _launch_created(cfg: Config, ref: TaskRef, *, interactive: bool = False) -> None:
    """Launch (or resume) a created recurring task.

    Recurring tasks create straight to `active` — machine-authored ready
    jobs, no separate activation step. An `in_progress` task is a *resume*: a
    past sweep died mid-run and left it frozen (`coga recurring` is a
    foreground command with no concurrent sweep, so it can only be an orphan),
    and `coga launch` re-composes it from its current `step:`. `done`/`paused`
    are left alone — re-launching finished or human-parked work would be wrong,
    and saying so beats silently doing nothing.
    """
    if not (ref.ticket_path).is_file():
        typer.secho(
            f"{ref.id_slug} was already handled on the control branch; not launching.",
            fg=typer.colors.BRIGHT_BLACK,
        )
        return

    ticket = read_ticket(ref)
    if ticket.status not in {"active", "in_progress"}:
        typer.secho(
            f"{ref.id_slug} is {ticket.status}; not launching.",
            fg=typer.colors.YELLOW,
        )
        return

    verb = "Resuming" if ticket.status == "in_progress" else "Launching"
    typer.echo(f"{verb} {ref.id_slug}")
    from coga.commands.launch import launch as launch_cmd

    idle_timeout = None if interactive else _recurring_idle_timeout(cfg)
    max_session = None if interactive else _recurring_max_session(cfg)
    launch_cmd(
        ref.id_slug,
        agent_override=None,
        prompt_report=False,
        idle_timeout=idle_timeout,
        max_session=max_session,
        return_timeout=False,
    )


def _stop_if_unfinished_after_launch(
    cfg: Config, ref: TaskRef, *, interactive: bool, timed_out: bool = False
) -> None:
    """Stop a bare recurring sweep if one launched task is still in flight.

    `interactive` is set when the sweep is `--interactive` (or the just-
    launched template's own `mode:` was interactive). In that case the human
    is driving — exiting the agent without marking done is a valid "park this
    run and move on" signal, not a stuck task. Make that durable by pausing the
    task, then continue instead of bailing the sweep; otherwise the next scan
    would treat the leftover `in_progress` state as a dead supervisor's orphan
    and relaunch it.

    `timed_out` is set when `launch` reported a liveness teardown (idle /
    max-session) — the agent wedged and never signalled done. That must NOT be
    recorded as the human-pause above: it isn't a deliberate park, it's a stuck
    run. We pause it (so the next scan doesn't relaunch the orphan) but log and
    broadcast it as a watchdog *timeout*, with a system actor, then continue the
    sweep so one wedge can't starve the tasks behind it.
    """
    if not (ref.ticket_path).exists():
        return

    ticket = read_ticket(ref)
    if ticket.status in {"done", "paused"}:
        return

    if timed_out:
        suffix = "liveness watchdog: REPL timed out before signalling done"
        try:
            mark_paused(
                cfg,
                ref,
                ticket,
                actor="system:watchdog",
                log_message=f"paused ({ticket.status} → paused) — {suffix}",
                slack_text=(
                    f"⏱️ *{ref.id_slug}* \"{ticket.title}\" timed out — {suffix}"
                ),
                digest_detail=f"→ paused (timeout) — {suffix}",
                echo=None,
            )
        except TaskValidationError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            sys.exit(2)
        typer.secho(
            f"{ref.id_slug}: timed out (status={ticket.status!r}); paused as a "
            "watchdog timeout and continuing to next due task.",
            fg=typer.colors.YELLOW,
        )
        return

    if interactive or ticket.mode == "agent":
        suffix = "Agent-mode recurring launch exited unfinished"
        try:
            mark_paused(
                cfg,
                ref,
                ticket,
                actor=f"human:{cfg.current_user}",
                log_message=f"paused ({ticket.status} → paused) — {suffix}",
                echo=None,
            )
        except TaskValidationError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            sys.exit(2)
        typer.secho(
            f"{ref.id_slug}: ended with status={ticket.status!r}; "
            "paused and continuing to next due task (interactive).",
            fg=typer.colors.YELLOW,
        )
        return

    typer.secho(
        f"{ref.id_slug}: recurring launch returned with status={ticket.status!r}; "
        "stopping before the next due task. Finish or delete this run, then "
        "rerun `coga recurring`.",
        fg=typer.colors.RED,
        err=True,
    )
    sys.exit(1)


# --- scan reporting -----------------------------------------------------------


def _env_seconds(name: str) -> tuple[bool, float | None]:
    """Read a seconds value from env var `name`.

    Returns `(present, value)`: `present` is False when the var is unset (so
    the caller falls back to config/default); when set, `value` is the parsed
    seconds or None for a `<= 0`, non-finite, or unparseable value (an explicit
    "disarm this backstop"). The env override always wins over config when set —
    even to disarm — so a machine can turn a committed default off locally.
    """
    raw = os.environ.get(name)
    if raw is None:
        return False, None
    try:
        seconds = float(raw)
    except ValueError:
        return True, None
    if not math.isfinite(seconds) or seconds <= 0:
        return True, None
    return True, seconds


def _recurring_idle_timeout(cfg) -> float | None:
    """Idle-timeout (seconds) for interactive REPLs the sweep spawns.

    Precedence: `COGA_REPL_IDLE_TIMEOUT` env override > `[launch].idle_timeout`
    in `coga.toml` (`cfg.launch_idle_timeout`) > the `_RECURRING_IDLE_TIMEOUT_
    SECONDS` default. A `<= 0`, non-finite (`inf`/`nan`), or unparseable env
    value disarms the backstop (returns None). Read-only — the value is passed
    explicitly to `coga launch`, never written back to the environment, so it
    cannot leak into the process or a spawned child.
    """
    present, value = _env_seconds("COGA_REPL_IDLE_TIMEOUT")
    if present:
        return value
    if cfg.launch_idle_timeout_present:
        return cfg.launch_idle_timeout
    return _RECURRING_IDLE_TIMEOUT_SECONDS


def _recurring_max_session(cfg) -> float | None:
    """Max-session wall-clock cap (seconds) for the REPLs the sweep spawns.

    Precedence: `COGA_REPL_MAX_SESSION` env override > `[launch].max_session`
    (`cfg.launch_max_session`) > None (no cap). Unlike idle-timeout there is no
    built-in default — a wall-clock cap is opt-in, since a legitimately long
    interactive step shouldn't be killed unless the team asked for it. A `<= 0`,
    non-finite, or unparseable env value disarms it.
    """
    present, value = _env_seconds("COGA_REPL_MAX_SESSION")
    if present:
        return value
    return cfg.launch_max_session


def _prepare_forced_launch(cfg: Config, task: DueTask) -> None:
    """Record a forced rerun only once the sweep reaches this task.

    `coga recurring --all` includes existing `done`/`paused` period tasks.
    Those tasks must not advance the parent high-water during scan: a prior
    task might stop the sequential sweep first. Once we reach the task, flip it
    back to `active`, then record the forced period and sync the real task.
    If the later launch preflight fails, the task is at least live for a future
    normal sweep instead of being silently skipped as already serviced.
    """
    if task.ref is None:
        return

    if not (task.ref.ticket_path).is_file():
        outcome = create_named(cfg, task.template)
        task.ref = outcome.ref
        task.created = outcome.created

    if not task.created:
        _sync_recurring_create(
            cfg,
            task.template,
            task.ref,
            respect_handled_period=False,
            respect_existing_task=False,
            restore_existing_control_task=True,
            overwrite_dirty_control_task=False,
            force_period_key=task.period_key,
            force_snapshot_is_fresh=False,
            force_record_period=False,
        )

    ticket = read_ticket(task.ref)
    task.status = ticket.status
    if not task.created and ticket.status in {"active", "in_progress"}:
        return

    if ticket.status not in {"active", "in_progress"}:
        prior = ticket.status
        mark_active(
            cfg,
            task.ref,
            ticket,
            actor=f"human:{cfg.current_user}",
            log_message=f"activated ({prior} → active) for forced recurring run",
            echo=f"{task.ref.id_slug}: active (forced recurring run)",
        )
        task.status = "active"
    _record_forced_period_locally(cfg, task)
    _sync_recurring_create(
        cfg,
        task.template,
        task.ref,
        respect_handled_period=False,
        respect_existing_task=False,
        restore_existing_control_task=False,
        overwrite_dirty_control_task=False,
    )


def _record_forced_period_locally(cfg: Config, task: DueTask) -> None:
    if task.ref is None or not task.period_key:
        return

    template_dir = recurring_dir(cfg) / task.template
    template = Template.load(template_dir)
    blackboard_text = (
        read_blackboard(template.ticket_path, blackboard_required=False)
        if template.ticket_path.is_file()
        else ""
    )
    state_keys = list(template.frontmatter.get("state_keys") or [])
    if state_keys:
        _write_snapshot_from_text(
            task.ref.path,
            template.name,
            blackboard_text,
            state_keys,
        )

    current = read_last_serviced_period(template.ticket_path)
    if current is not None and current >= task.period_key:
        return
    write_last_serviced_period(template.ticket_path, task.period_key)
    _append_forced_reused_log(cfg, template.ticket_path, task.ref.id_slug, task.period_key)


def _broadcast_scan(
    cfg,
    scan: DueScan,
    *,
    respect_handled_period: bool = True,
    sync_existing: bool = False,
) -> None:
    """Post Slack lines for newly created tasks and skipped templates.

    In `--all` mode, also refresh existing task status from the control branch
    before the launch list is sorted. A stale local `done` copy may be an
    `in_progress` orphan on control, and resume-first ordering depends on the
    current status. The actual restore/sync still happens when the launch loop
    reaches that task, so an unreached task is not mutated during the scan.
    """
    for task in list(scan.tasks):
        if not task.created:
            if sync_existing:
                _refresh_forced_status_from_control(cfg, task)
            continue
        if task.ref is None:
            continue
        created_on_control = _sync_recurring_create(
            cfg,
            task.template,
            task.ref,
            respect_handled_period=respect_handled_period,
            respect_existing_task=not sync_existing,
            restore_existing_control_task=sync_existing,
            overwrite_dirty_control_task=sync_existing and task.created,
            force_period_key=task.period_key if sync_existing else None,
            force_snapshot_is_fresh=False,
            force_record_period=False,
        )
        if not (task.ref.ticket_path).is_file():
            scan.tasks.remove(task)
            typer.secho(
                f"{task.ref.id_slug} was already handled on the control branch; "
                "not launching.",
                fg=typer.colors.BRIGHT_BLACK,
            )
            continue
        ticket = read_ticket(task.ref)
        task.status = ticket.status
        if sync_existing and not created_on_control:
            task.created = False
        if task.created and created_on_control:
            typer.echo(f"Created {task.ref.id_slug}")

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


def _print_table(scan: DueScan, *, force: bool = False) -> None:
    """Print a one-line-per-template scan summary."""
    if not scan.tasks and not scan.errors:
        return

    now = datetime.now()
    typer.echo(f"Recurring scan — {now:%Y-%m-%d %H:%M}\n")
    for task in scan.tasks:
        when = _firing_label(task.last_fire, now)
        if task.ref is None:
            # The period was created earlier this cycle and the task
            # was removed afterwards (a later Dream retro pass or `coga delete`).
            action = typer.style(
                "skip (ran this period)", fg=typer.colors.BRIGHT_BLACK
            )
        elif task.resuming:
            # An orphaned `in_progress` period task from a dead sweep — relaunch
            # resumes its current step rather than starting a fresh run.
            action = typer.style("→ resume", fg=typer.colors.YELLOW)
        elif task.launchable or force:
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
