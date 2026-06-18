"""`relay recurring` — scan recurring templates and launch what's due."""

from __future__ import annotations

import math
import os
import subprocess
import shutil
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from relay import git
from relay.commands.launch import _interactive_stdio_has_tty
from relay.config import Config, ConfigError, load_config
from relay.logfile import append_log
from relay.recurring import (
    DueScan,
    RecurringError,
    TemplateStatus,
    list_templates,
    merge_last_serviced_period_text,
    read_last_serviced_period,
    recurring_dir,
    create_named,
    scan_due,
)
from relay.mark import mark_paused
from relay.notification import notify
from relay.tasks import TaskRef, list_tasks, read_ticket
from relay.ticket import TicketError
from relay.validate import TaskValidationError

# Default idle-timeout backstop (seconds) the sweep arms on the interactive
# REPLs it spawns: one that stalls or crashes before signalling done would
# otherwise block the sequential sweep forever — the hang this command was seen
# to hit. Generous enough that a slow-but-progressing agent (which streams PTY
# output) never trips it; only a genuinely silent REPL does. `--interactive`
# (a human driving by hand) leaves it off; `RELAY_REPL_IDLE_TIMEOUT` overrides
# the window or, at `<= 0` / non-finite, disarms it.
_RECURRING_IDLE_TIMEOUT_SECONDS = 900.0

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
        help="Force a real, full run of EVERY template: bypass the schedule "
        "and the already-serviced/done/paused status filter, then get-or-create "
        "and launch each template's real `recurring/<name>` task. Identical to a "
        "bare `relay recurring` (real Slack, spool drain, git sync, "
        "`last_serviced_period` advance) — just forced. A template that already "
        "ran this period is re-launched (relay launch re-activates a finished "
        "ticket).",
    ),
) -> None:
    """Scan every recurring template and launch any due tasks, sequentially.

    Bare `relay recurring` is the default action. For each template under
    `relay-os/recurring/` it get-or-creates the current period's task, then
    launches every one still `active` or orphaned `in_progress` —
    most-overdue first, one at a time. A period task left `in_progress` by a
    sweep whose supervisor died mid-run (laptop sleep, SSH drop) is **resumed**
    from its current step on the next sweep. If an interactive launch returns
    unfinished, the sweep pauses it before continuing, so a frozen
    `in_progress` can still mean "dead run's orphan". `done` and `paused` tasks
    are skipped. Current period only: running this once a month for a weekly
    template produces one run, not a backlog. It does not install or manage
    system cron; nothing runs unless you invoke it.

    `--all` forces a real, full run: the only difference from the bare sweep is
    that it ignores the schedule and the status filter, so every template is
    launched — including ones already serviced this period (re-launched) and
    `done`/`paused` ones (`relay launch` re-activates them). Everything else —
    Slack, the digest spool, git task-state sync, the `last_serviced_period`
    high-water advance — is identical to a normal run.

    `relay recurring launch <name>` force-runs one named template now.
    """
    if ctx.invoked_subcommand is not None:
        return

    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    scan = scan_due(
        cfg, allow_interactive=_interactive_stdio_has_tty(), force=all_
    )
    _broadcast_scan(cfg, scan)
    _print_table(scan)

    # `--all` force-launches every materialized task regardless of status;
    # the bare sweep launches only the launchable (active/in_progress) ones.
    due = scan.forced if all_ else scan.due
    if not due:
        typer.echo(
            "No recurring templates to launch." if all_ else "No recurring tasks due."
        )
        return

    mode_override = "interactive" if interactive else None
    # `--interactive` is a human stepping through by hand, so leave the spawned
    # REPL unbounded; an automatic sweep arms the liveness backstops so one stuck
    # agent can't block the tasks behind it.
    idle_timeout = None if interactive else _recurring_idle_timeout(cfg)
    max_session = None if interactive else _recurring_max_session(cfg)
    label = "task(s)" if all_ else "due task(s)"
    typer.echo(f"\nLaunching {len(due)} {label} sequentially...\n")
    from relay.commands.launch import launch as launch_cmd

    for i, task in enumerate(due, 1):
        typer.secho(
            f"[{i}/{len(due)}] {task.ref.id_slug}", fg=typer.colors.CYAN, bold=True
        )
        # Sequential by design: each launch blocks until the agent session
        # exits before the next begins. `scan_due` filters out templates that
        # cannot run in the current stdio context (interactive with no TTY), and
        # the liveness backstops release any that launch but then stall. `launch`
        # returns "timeout" when a backstop fired so we record the wedge honestly
        # below instead of pausing it as a human would.
        kind = launch_cmd(
            task.ref.id_slug,
            agent_override=None,
            prompt_report=False,
            no_verify=False,
            mode_override=mode_override,
            idle_timeout=idle_timeout,
            max_session=max_session,
            return_timeout=True,
        )
        _stop_if_unfinished_after_launch(
            cfg, task.ref, interactive=interactive, timed_out=(kind == "timeout")
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
    """Create a named recurring template now and launch it.

    Ignores the template's schedule — the on-demand entry point behind
    aliases like `relay dream`. The task slug is the stable qualified
    `recurring/<name>`, so this and a bare `relay recurring` converge on one
    instantiated task directory.
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    try:
        outcome = create_named(cfg, name)
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    ref = outcome.ref
    if outcome.created:
        created_on_control = _sync_recurring_create(
            cfg, name, ref, respect_handled_period=False
        )
        if not (ref.path / "ticket.md").is_file():
            typer.secho(
                f"{ref.id_slug} was already handled on the control branch; "
                "not launching.",
                fg=typer.colors.BRIGHT_BLACK,
            )
            return
        if created_on_control:
            typer.echo(f"Created {ref.id_slug}")
    else:
        typer.echo(f"{ref.id_slug} already created for this period")

    _launch_created(ref, mode_override="interactive" if interactive else None)


@app.command("list")
def list_recurring() -> None:
    """List recurring templates with their schedules, plus instantiated tasks.

    Read-only — the inspectable counterpart of a bare `relay recurring`, which
    get-or-creates each due period's task and launches it. This creates
    nothing and launches nothing (principle 6: a view never mutates). Two
    tables: every template with its schedule and the current period's state,
    then the picked tasks — the recurring period tasks already on disk.
    """
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)

    statuses = list_templates(cfg)
    picked = [ref for ref in list_tasks(cfg) if ref.directory == "recurring"]

    if not statuses and not picked:
        typer.echo("(no recurring templates)")
        return

    console = Console()
    now = datetime.now()
    _print_templates_table(console, statuses, now)
    _print_picked_table(console, picked)


def _print_templates_table(
    console: Console, statuses: list[TemplateStatus], now: datetime
) -> None:
    if not statuses:
        return
    table = Table(title="Recurring templates", title_justify="left", show_edge=False)
    for col in ("template", "schedule", "last fire", "next fire", "current period"):
        table.add_column(col, no_wrap=True)
    for s in sorted(statuses, key=lambda x: x.name):
        if s.error:
            table.add_row(s.name, f"[red]error: {s.error}[/red]", "-", "-", "-")
            continue
        if s.instance is not None:
            period = f"{s.instance_status} · {s.instance.id_slug}"
        elif s.due:
            period = "[green]due — not created[/green]"
        else:
            period = "none"
        table.add_row(
            s.name,
            s.schedule or "-",
            _firing_stamp(s.last_fire),
            _firing_stamp(s.next_fire),
            period,
        )
    console.print(table)


def _print_picked_table(console: Console, picked: list[TaskRef]) -> None:
    if not picked:
        console.print("No instantiated recurring tasks.", style="dim")
        return
    table = Table(
        title="Picked tasks (instantiated)",
        title_justify="left",
        show_edge=False,
    )
    for col in ("slug", "status", "step", "mode"):
        table.add_column(col, no_wrap=True)
    for ref in picked:
        try:
            ticket = read_ticket(ref)
        except TicketError:
            table.add_row(ref.id_slug, "(unreadable)", "-", "-")
            continue
        table.add_row(
            ref.id_slug,
            ticket.status or "-",
            ticket.step or "-",
            ticket.mode or "-",
        )
    console.print(table)


def _firing_stamp(when: datetime | None) -> str:
    """Compact firing label for the templates table (`Mon 06-15 09:00`)."""
    if when is None:
        return "-"
    return when.strftime("%a %m-%d %H:%M")


def _launch_created(ref: TaskRef, *, mode_override: str | None = None) -> None:
    """Launch (or resume) a created recurring task.

    Recurring tasks create straight to `active` — machine-authored ready
    jobs, no separate activation step. An `in_progress` task is a *resume*: a
    past sweep died mid-run and left it frozen (`relay recurring` is a
    foreground command with no concurrent sweep, so it can only be an orphan),
    and `relay launch` re-composes it from its current `step:`. `done`/`paused`
    are left alone — re-launching finished or human-parked work would be wrong,
    and saying so beats silently doing nothing.
    """
    if not (ref.path / "ticket.md").is_file():
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
    from relay.commands.launch import launch as launch_cmd

    launch_cmd(
        ref.id_slug,
        agent_override=None,
        prompt_report=False,
        no_verify=False,
        mode_override=mode_override,
        return_timeout=False,
    )


def _sync_recurring_create(
    cfg: Config,
    template_name: str,
    ref: TaskRef,
    *,
    respect_handled_period: bool = True,
) -> bool:
    """Sync the period task and high-water line that make deletion idempotent."""
    template_dir = recurring_dir(cfg) / template_name
    message = f"Ticket: {ref.id_slug} — recurring create"
    if not template_dir.is_dir():
        git.sync_paths(
            cfg,
            ref.path,
            [ref.path],
            message=message,
        )
        return True
    template_log = template_dir / "log.md"
    template_blackboard = template_dir / "blackboard.md"
    original_log = template_log.read_text() if template_log.is_file() else ""
    local_log = original_log
    original_blackboard = (
        template_blackboard.read_text() if template_blackboard.is_file() else ""
    )
    local_blackboard = original_blackboard
    period_key = read_last_serviced_period(template_blackboard)
    restore_log = original_log
    restore_blackboard = original_blackboard
    created_on_control = True
    try:
        (
            restore_log,
            restore_blackboard,
            created_on_control,
        ) = _sync_recurring_create_paths(
            cfg,
            anchor_path=ref.path,
            paths=[ref.path, template_log, template_blackboard],
            template_log=template_log,
            template_blackboard=template_blackboard,
            original_log=original_log,
            local_log=local_log,
            original_blackboard=original_blackboard,
            local_blackboard=local_blackboard,
            period_key=period_key,
            message=message,
            respect_handled_period=respect_handled_period,
        )
    finally:
        template_log.write_text(restore_log)
        template_blackboard.write_text(restore_blackboard)
    return created_on_control


def _sync_recurring_create_paths(
    cfg: Config,
    *,
    anchor_path: Path,
    paths: list[Path],
    template_log: Path,
    template_blackboard: Path,
    original_log: str,
    local_log: str,
    original_blackboard: str,
    local_blackboard: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
) -> tuple[str, str, bool]:
    """Sync create paths while merging recurring log/history state."""
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return original_log, original_blackboard, True

    root = _git_toplevel(anchor_path)
    if root is None:
        sys.stderr.write(f"[git] not a git repo (sync skipped): {message}\n")
        return original_log, original_blackboard, True

    try:
        rels = [_relative_to_root(root, path) for path in paths]
        log_rel = _relative_to_root(root, template_log)
        blackboard_rel = _relative_to_root(root, template_blackboard)
        template_ticket_rel = _relative_to_root(root, template_log.parent / "ticket.md")
        branch = _current_branch(root)

        try:
            _fetch_control_branch(cfg, root)
        except git.GitError:
            template_log.write_text(local_log)
            template_blackboard.write_text(local_blackboard)
            git.sync_paths(cfg, anchor_path, paths, message=message)
            return original_log, original_blackboard, True
        base = _rev_parse(root, "FETCH_HEAD")
        task_rel = _relative_to_root(root, anchor_path)
        if _control_already_has_period(
            root,
            base,
            blackboard_rel,
            task_rel,
            period_key=period_key,
            include_ledger=respect_handled_period,
        ):
            if branch == cfg.git_control_branch:
                _restore_selected_paths_from_ref(root, "HEAD", rels)
                _rebase_checked_out_branch_onto(root, base)
                return (
                    _control_log(root, "HEAD", log_rel),
                    _control_blackboard_with_local_period(
                        root, "HEAD", blackboard_rel, original_blackboard
                    ),
                    False,
                )
            _restore_selected_paths_from_ref(root, base, rels)
            if branch != "HEAD":
                git._commit_paths(root, rels, message)
                return (
                    _control_log(root, "HEAD", log_rel),
                    _control_blackboard_with_local_period(
                        root, "HEAD", blackboard_rel, original_blackboard
                    ),
                    False,
                )
            return (
                _control_log(root, base, log_rel),
                _control_blackboard_with_local_period(
                    root, base, blackboard_rel, original_blackboard
                ),
                False,
            )
        _write_merged_log_for_ref(root, template_log, log_rel, base, local_log)
        _write_merged_blackboard_for_ref(
            root, template_blackboard, blackboard_rel, base, local_blackboard
        )

        if branch == cfg.git_control_branch:
            return _sync_recurring_create_on_checked_out_control_branch(
                cfg,
                root,
                rels,
                template_log=template_log,
                template_blackboard=template_blackboard,
                log_rel=log_rel,
                blackboard_rel=blackboard_rel,
                template_ticket_rel=template_ticket_rel,
                original_log=original_log,
                local_log=local_log,
                original_blackboard=original_blackboard,
                local_blackboard=local_blackboard,
                period_key=period_key,
                message=message,
                respect_handled_period=respect_handled_period,
            )

        committed_log = template_log.read_text()
        committed_blackboard = template_blackboard.read_text()
        if branch == "HEAD":
            sys.stderr.write(
                f"[git] detached HEAD — task state landed on "
                f"{cfg.git_control_branch!r} but not committed locally. ({message})\n"
            )
        else:
            git._commit_paths(root, rels, message)
            committed_log = _show_path(root, "HEAD", log_rel)
            committed_blackboard = _show_path(root, "HEAD", blackboard_rel)
        landed, already_handled = _land_recurring_create_on_control_branch(
            cfg,
            root,
            rels,
            template_log=template_log,
            template_blackboard=template_blackboard,
            log_rel=log_rel,
            blackboard_rel=blackboard_rel,
            template_ticket_rel=template_ticket_rel,
            task_rel=task_rel,
            local_log=local_log,
            local_blackboard=local_blackboard,
            period_key=period_key,
            message=message,
            respect_handled_period=respect_handled_period,
        )
        if already_handled:
            _restore_selected_paths_from_ref(root, landed, rels)
            if branch != "HEAD":
                git._commit_paths(root, rels, message)
                return (
                    _control_log(root, "HEAD", log_rel),
                    _control_blackboard_with_local_period(
                        root, "HEAD", blackboard_rel, original_blackboard
                    ),
                    False,
                )
            return (
                _control_log(root, landed, log_rel),
                _control_blackboard_with_local_period(
                    root, landed, blackboard_rel, original_blackboard
                ),
                False,
            )
        return (
            _merge_log_entries(committed_log, original_log),
            merge_last_serviced_period_text(committed_blackboard, original_blackboard),
            True,
        )
    except git.GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        _append_sync_failure(anchor_path, exc)
        return original_log, original_blackboard, True


def _control_log(root: Path, ref: str, log_rel: str) -> str:
    """The recurring template `log.md` as committed on `ref` (control branch),
    normalized through the append-only merge."""
    return _merge_log_entries(_show_path(root, ref, log_rel))


def _control_blackboard_with_local_period(
    root: Path, ref: str, blackboard_rel: str, original_blackboard: str
) -> str:
    return merge_last_serviced_period_text(
        _show_path(root, ref, blackboard_rel), original_blackboard
    )


def _merge_log_entries(*texts: str) -> str:
    """Merge append-only log lines, preserving first-seen order."""
    out: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for line in text.splitlines():
            if line in seen:
                continue
            seen.add(line)
            out.append(line)
    return "".join(f"{line}\n" for line in out)


def _append_sync_failure(anchor_path: Path, exc: Exception) -> None:
    """Best-effort task log note for non-fatal git sync failures."""
    if not anchor_path.is_dir():
        return
    try:
        append_log(anchor_path, "git", f"sync failed: {exc}")
    except OSError:
        return


def _land_recurring_create_on_control_branch(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    template_log: Path,
    template_blackboard: Path,
    log_rel: str,
    blackboard_rel: str,
    template_ticket_rel: str,
    task_rel: str,
    local_log: str,
    local_blackboard: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
) -> tuple[str, bool]:
    remote = cfg.git_remote
    branch = cfg.git_control_branch

    for _ in range(git._MAX_SYNC_ATTEMPTS):
        _fetch_control_branch(cfg, root)
        base = _rev_parse(root, "FETCH_HEAD")
        if _control_already_has_period(
            root,
            base,
            blackboard_rel,
            task_rel,
            period_key=period_key,
            include_ledger=respect_handled_period,
        ):
            return base, True
        _write_merged_log_for_ref(root, template_log, log_rel, base, local_log)
        _write_merged_blackboard_for_ref(
            root, template_blackboard, blackboard_rel, base, local_blackboard
        )
        control_rels = _control_create_rels(root, base, rels, template_ticket_rel)

        tree = git._build_overlay_tree(root, base, control_rels)
        if tree == _rev_parse(root, f"{base}^{{tree}}"):
            return base, False

        new = git._run_git(root, "commit-tree", tree, "-p", base, "-m", message).strip()
        result = git._push_ref(root, remote, f"{new}:refs/heads/{branch}")
        if result is None:
            git._try_update_local_ref(root, branch, new)
            return new, False
        if not git._is_non_fast_forward(result):
            raise git.GitError(
                f"`git push {remote} {new}:refs/heads/{branch}` failed: {result}"
            )

    raise git.GitError(
        f"could not land on {branch!r} after {git._MAX_SYNC_ATTEMPTS} attempts — "
        f"contention on refs/heads/{branch}"
    )


def _sync_recurring_create_on_checked_out_control_branch(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    template_log: Path,
    template_blackboard: Path,
    log_rel: str,
    blackboard_rel: str,
    template_ticket_rel: str,
    original_log: str,
    local_log: str,
    original_blackboard: str,
    local_blackboard: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
) -> tuple[str, str, bool]:
    landed, already_handled = _land_recurring_create_on_control_branch(
        cfg,
        root,
        rels,
        template_log=template_log,
        template_blackboard=template_blackboard,
        log_rel=log_rel,
        blackboard_rel=blackboard_rel,
        template_ticket_rel=template_ticket_rel,
        task_rel=rels[0],
        local_log=local_log,
        local_blackboard=local_blackboard,
        period_key=period_key,
        message=message,
        respect_handled_period=respect_handled_period,
    )
    if already_handled:
        _restore_selected_paths_from_ref(root, "HEAD", rels)
        _rebase_checked_out_branch_onto(root, landed)
        git._push_control_branch(cfg, root)
        return (
            _control_log(root, "HEAD", log_rel),
            _control_blackboard_with_local_period(
                root, "HEAD", blackboard_rel, original_blackboard
            ),
            False,
        )

    _restore_selected_paths_from_ref(root, "HEAD", rels)
    _rebase_checked_out_branch_onto(root, landed)
    git._push_control_branch(cfg, root)
    return (
        _merge_log_entries(_show_path(root, "HEAD", log_rel), original_log),
        merge_last_serviced_period_text(
            _show_path(root, "HEAD", blackboard_rel), original_blackboard
        ),
        True,
    )


def _control_create_rels(
    root: Path, ref: str, rels: list[str], template_ticket_rel: str
) -> list[str]:
    if _ref_has_path(root, ref, template_ticket_rel):
        return rels
    return rels[:1]


def _control_already_has_period(
    root: Path,
    ref: str,
    blackboard_rel: str,
    task_rel: str,
    *,
    period_key: str | None,
    include_ledger: bool = True,
) -> bool:
    if _ref_has_path(root, ref, task_rel):
        return True
    if not include_ledger or period_key is None:
        return False
    serviced = _read_control_last_serviced_period(root, ref, blackboard_rel)
    return serviced is not None and serviced >= period_key


def _restore_selected_paths_from_ref(root: Path, ref: str, rels: list[str]) -> None:
    for rel in rels:
        if _ref_has_path(root, ref, rel):
            git._run_git(
                root, "restore", "--source", ref, "--staged", "--worktree", "--", rel
            )
            continue
        git._run_git(root, "rm", "-rf", "--cached", "--ignore-unmatch", "--", rel)
        path = Path(rel) if Path(rel).is_absolute() else root / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def _ref_has_path(root: Path, ref: str, rel: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{ref}:{rel}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _rebase_checked_out_branch_onto(root: Path, target: str) -> None:
    if _rev_parse(root, "HEAD") == target:
        return

    proc = subprocess.run(
        ["git", "-C", str(root), "-c", "rebase.autoStash=true", "rebase", target],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return

    subprocess.run(
        ["git", "-C", str(root), "rebase", "--abort"],
        capture_output=True,
        text=True,
        check=False,
    )
    raise git.GitError(
        f"could not rebase checked-out control branch onto {target}: "
        f"{(proc.stderr + proc.stdout).strip()}"
    )


def _write_merged_log_for_ref(
    root: Path, template_log: Path, log_rel: str, ref: str, local_log: str
) -> None:
    control_log = _show_path(root, ref, log_rel)
    template_log.write_text(
        _merge_log_entries(control_log, local_log)
    )


def _write_merged_blackboard_for_ref(
    root: Path,
    template_blackboard: Path,
    blackboard_rel: str,
    ref: str,
    local_blackboard: str,
) -> None:
    control_blackboard = _show_path(root, ref, blackboard_rel)
    template_blackboard.write_text(
        merge_last_serviced_period_text(control_blackboard, local_blackboard)
    )


def _read_control_last_serviced_period(
    root: Path, ref: str, blackboard_rel: str
) -> str | None:
    text = _show_path(root, ref, blackboard_rel)
    if not text:
        return None
    tmp = merge_last_serviced_period_text("", text)
    marker = "last_serviced_period: "
    for line in tmp.splitlines():
        if line.startswith(marker):
            return line[len(marker):].strip() or None
    return None


def _show_path(root: Path, ref: str, rel: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"{ref}:{rel}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def _fetch_control_branch(cfg: Config, root: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "fetch", cfg.git_remote, cfg.git_control_branch],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise git.GitError("`git` not found on PATH") from exc
    if result.returncode != 0:
        raise git.GitError(
            f"`git fetch {cfg.git_remote} {cfg.git_control_branch}` failed "
            f"(exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def _rev_parse(root: Path, ref: str) -> str:
    return git._run_git(root, "rev-parse", ref).strip()


def _current_branch(root: Path) -> str:
    return git._run_git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def _git_toplevel(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    top = result.stdout.strip()
    return Path(top) if top else None


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
    if not (ref.path / "ticket.md").exists():
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

    if interactive or ticket.mode == "interactive":
        suffix = "interactive recurring launch exited unfinished"
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
        "rerun `relay recurring`.",
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

    Precedence: `RELAY_REPL_IDLE_TIMEOUT` env override > `[launch].idle_timeout`
    in `relay.toml` (`cfg.launch_idle_timeout`) > the `_RECURRING_IDLE_TIMEOUT_
    SECONDS` default. A `<= 0`, non-finite (`inf`/`nan`), or unparseable env
    value disarms the backstop (returns None). Read-only — the value is passed
    explicitly to `relay launch`, never written back to the environment, so it
    cannot leak into the process or a spawned child.
    """
    present, value = _env_seconds("RELAY_REPL_IDLE_TIMEOUT")
    if present:
        return value
    if cfg.launch_idle_timeout_present:
        return cfg.launch_idle_timeout
    return _RECURRING_IDLE_TIMEOUT_SECONDS


def _recurring_max_session(cfg) -> float | None:
    """Max-session wall-clock cap (seconds) for the REPLs the sweep spawns.

    Precedence: `RELAY_REPL_MAX_SESSION` env override > `[launch].max_session`
    (`cfg.launch_max_session`) > None (no cap). Unlike idle-timeout there is no
    built-in default — a wall-clock cap is opt-in, since a legitimately long
    interactive step shouldn't be killed unless the team asked for it. A `<= 0`,
    non-finite, or unparseable env value disarms it.
    """
    present, value = _env_seconds("RELAY_REPL_MAX_SESSION")
    if present:
        return value
    return cfg.launch_max_session


def _broadcast_scan(cfg, scan: DueScan) -> None:
    """Post Slack lines for newly created tasks and skipped templates."""
    for task in list(scan.tasks):
        if not task.created:
            continue
        created_on_control = _sync_recurring_create(cfg, task.template, task.ref)
        if not (task.ref.path / "ticket.md").is_file():
            scan.tasks.remove(task)
            typer.secho(
                f"{task.ref.id_slug} was already handled on the control branch; "
                "not launching.",
                fg=typer.colors.BRIGHT_BLACK,
            )
            continue
        ticket = read_ticket(task.ref)
        task.status = ticket.status
        if created_on_control:
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


def _print_table(scan: DueScan) -> None:
    """Print a one-line-per-template scan summary."""
    if not scan.tasks and not scan.errors:
        return

    now = datetime.now()
    typer.echo(f"Recurring scan — {now:%Y-%m-%d %H:%M}\n")
    for task in scan.tasks:
        when = _firing_label(task.last_fire, now)
        if task.ref is None:
            # The period was created earlier this cycle and the task
            # was removed afterwards (a later Dream retro pass or `relay delete`).
            action = typer.style(
                "skip (ran this period)", fg=typer.colors.BRIGHT_BLACK
            )
        elif task.resuming:
            # An orphaned `in_progress` period task from a dead sweep — relaunch
            # resumes its current step rather than starting a fresh run.
            action = typer.style("→ resume", fg=typer.colors.YELLOW)
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
