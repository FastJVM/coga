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

from relay import git
from relay.commands.launch import _interactive_stdio_has_tty
from relay.config import Config, ConfigError, load_config
from relay.logfile import append_log
from relay.recurring import (
    DueScan,
    RecurringError,
    is_debug_slug,
    recurring_dir,
    scaffold_named,
    scan_debug,
    scan_due,
)
from relay.mark import mark_paused
from relay.paths import tasks_dir
from relay.slack import notify
from relay.tasks import TaskRef, read_ticket
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
        help="Debug: ignore the schedule and status filter — scaffold a fresh "
        "throwaway run of EVERY template and launch them all, regardless of "
        "whether this period already ran. Real period tasks are left "
        "untouched; each throwaway run's outcome is appended to its template's "
        "log.md and the scratch dir is removed when it finishes, so nothing "
        "lingers in `relay status`.",
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

    # Take over on relaunch: clear any debug scratch a crashed prior sweep left
    # behind before doing anything else. Runs for both the bare sweep and `--all`.
    _reap_debug_orphans(cfg)

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
    # `--interactive` is a human stepping through by hand, so leave the spawned
    # REPL unbounded; an automatic sweep arms the idle backstop so one stuck
    # agent can't block the tasks behind it.
    idle_timeout = None if interactive else _recurring_idle_timeout()
    typer.echo(f"\nLaunching {len(due)} due task(s) sequentially...\n")
    from relay.commands.launch import launch as launch_cmd

    for i, task in enumerate(due, 1):
        typer.secho(
            f"[{i}/{len(due)}] {task.ref.id_slug}", fg=typer.colors.CYAN, bold=True
        )
        # Sequential by design: each launch blocks until the agent session
        # exits before the next begins. `scan_due` filters out templates that
        # cannot run in the current stdio context (interactive with no TTY), and
        # the idle backstop releases any that launch but then stall.
        launch_cmd(
            task.ref.slug,
            agent_override=None,
            prompt_report=False,
            no_verify=False,
            mode_override=mode_override,
            idle_timeout=idle_timeout,
        )
        _stop_if_unfinished_after_launch(cfg, task.ref, interactive=interactive)


def _launch_all_debug(cfg) -> None:
    """Scaffold and launch a fresh throwaway run of every template (`--all`).

    Debug-only. The runs are disposable scratch, not real recurring work: they
    never broadcast to Slack or commit task state (`git.sync_task_state`
    suppresses the `-dbg-<digit>` slug, so nothing they do reaches git history),
    and the sweep never bails on an unfinished run (the human is driving).
    `_finalize_debug_run` rmtrees each run as it completes; `_reap_debug_orphans`
    (run at sweep start) clears any dir a crashed earlier sweep left behind.
    Script templates run as scripts; everything else launches interactively so
    there is a live console to watch.
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
    # the rest of the debug sweep.
    idle_timeout = _recurring_idle_timeout()

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
            idle_timeout=idle_timeout,
        )
        # A debug run has no persistent identity: record its outcome on the
        # template's own log.md (never composed into any prompt — see
        # compose_prompt, which only loads blackboard.md), then remove the
        # throwaway scratch dir so it never pollutes `relay status`.
        _finalize_debug_run(cfg, task)


def _read_debug_outcome(scratch) -> tuple[str, bool]:
    """Best-effort `(status, panicked)` for a debug run's scratch dir.

    Reads the ticket status and scans the blackboard for a `relay panic`
    marker, swallowing any error — the dir may be half-written or already
    gone. `relay panic` leaves the ticket `in_progress` and writes the marker
    to the blackboard, so the two signals together distinguish a panic from a
    plain unfinished run. Shared by `_finalize_debug_run` (clean completion)
    and `_reap_debug_orphans` (crashed-sweep cleanup) so both fold the same
    outcome vocabulary into the template log.
    """
    try:
        status = read_ticket(TaskRef(slug=scratch.name, path=scratch)).status
    except Exception:  # dir already gone / unreadable — nothing to fold back
        status = "unknown"
    panicked = False
    bb = scratch / "blackboard.md"
    if bb.is_file():
        try:
            panicked = "PANIC" in bb.read_text()
        except OSError:
            pass
    return status, panicked


def _finalize_debug_run(cfg: Config, task) -> None:
    """Fold a `--all` debug run back into the template log and delete its dir.

    Read the post-run ticket status (and a panic line, if any) *before*
    removing the scratch dir, append a one-line outcome to the recurring
    template's `log.md`, then `rmtree` the disposable task directory. The
    template log is an audit trail only — it is never part of prompt
    composition, so it can grow without bloating any agent's context.
    """
    scratch = task.ref.path
    status, panicked = _read_debug_outcome(scratch)

    if status == "done":
        outcome = "completed → done"
    elif panicked:
        outcome = "panicked (ended in_progress) — see prior session logs"
    else:
        outcome = f"ended {status!r} without `relay mark done`"

    template_dir = recurring_dir(cfg) / task.template
    if template_dir.is_dir():
        append_log(template_dir, "system", f"debug run {task.ref.slug}: {outcome}")

    shutil.rmtree(scratch, ignore_errors=True)
    typer.secho(
        f"  {task.ref.id_slug}: {outcome} — scratch dir removed, "
        f"logged to recurring/{task.template}/log.md",
        fg=typer.colors.BRIGHT_BLACK,
    )


def _reap_debug_orphans(cfg: Config) -> None:
    """Remove `*-dbg-*` scratch dirs a crashed prior `--all` sweep left behind.

    A `relay recurring --all` debug run is disposable scratch (see
    `scaffold_debug_run`); `_finalize_debug_run` rmtrees it when the run
    completes. If the sweep dies mid-run (laptop sleep, SSH drop) that cleanup
    never fires and the scratch dir is orphaned. Because debug runs never commit
    task state (`git.sync_task_state` suppresses the `-dbg-<digit>` slug), the
    orphan lives only in the working tree — there is nothing to uncommit, so
    reaping is a log-then-`rmtree`.

    Run at the start of every `relay recurring` (bare or `--all`): the sweep is a
    foreground command with no concurrent peer, so a `-dbg-<digit>` dir present
    when it starts cannot belong to a live run — it is always a dead sweep's
    litter. This is the "relay takes over and cleans up on relaunch" guarantee,
    the debug-run analogue of resuming an orphaned `in_progress` period task.

    Before deleting each orphan, fold its outcome into the originating
    template's `log.md` — which period it was and how it ended — so a crashed
    sweep's run is recorded, not silently erased. This mirrors the audit trail
    `_finalize_debug_run` writes on a clean completion; the template is the
    slug up to its `-dbg-<stamp>` infix.
    """
    tasks_root = tasks_dir(cfg)
    if not tasks_root.is_dir():
        return
    reaped: list[str] = []
    for entry in sorted(tasks_root.iterdir()):
        if entry.is_dir() and is_debug_slug(entry.name):
            status, panicked = _read_debug_outcome(entry)
            ended = "panicked" if panicked else f"ended {status!r}"
            template = entry.name.rsplit("-dbg-", 1)[0]
            template_dir = recurring_dir(cfg) / template
            if template_dir.is_dir():
                append_log(
                    template_dir,
                    "system",
                    f"orphaned debug run {entry.name} reaped: {ended} "
                    "(prior sweep died before cleanup)",
                )
            shutil.rmtree(entry, ignore_errors=True)
            reaped.append(entry.name)
    if reaped:
        typer.secho(
            f"Reaped {len(reaped)} orphaned debug run(s) from a prior sweep: "
            f"{', '.join(reaped)}",
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
        created_on_control = _sync_recurring_scaffold(
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
        typer.echo(f"{ref.id_slug} already scaffolded for this period")

    _launch_scaffolded(ref, mode_override="interactive" if interactive else None)


def _launch_scaffolded(ref: TaskRef, *, mode_override: str | None = None) -> None:
    """Launch (or resume) a scaffolded recurring task.

    Recurring tasks scaffold straight to `active` — machine-authored ready
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
        ref.slug,
        agent_override=None,
        prompt_report=False,
        no_verify=False,
        mode_override=mode_override,
    )


def _sync_recurring_scaffold(
    cfg: Config,
    template_name: str,
    ref: TaskRef,
    *,
    respect_handled_period: bool = True,
) -> bool:
    """Sync the period task and the ledger line that makes deletion idempotent."""
    template_log = recurring_dir(cfg) / template_name / "log.md"
    if not template_log.is_file():
        git.sync_paths(
            cfg,
            ref.path,
            [ref.path],
            message=f"Ticket: {ref.id_slug} — recurring scaffold",
        )
        return True

    original_log = template_log.read_text()
    local_log = _without_debug_log_entries(original_log)
    message = f"Ticket: {ref.id_slug} — recurring scaffold"
    restore_log = original_log
    created_on_control = True
    try:
        restore_log, created_on_control = _sync_recurring_scaffold_paths(
            cfg,
            anchor_path=ref.path,
            paths=[ref.path, template_log],
            template_log=template_log,
            original_log=original_log,
            local_log=local_log,
            message=message,
            respect_handled_period=respect_handled_period,
        )
    finally:
        template_log.write_text(restore_log)
    return created_on_control


def _sync_recurring_scaffold_paths(
    cfg: Config,
    *,
    anchor_path: Path,
    paths: list[Path],
    template_log: Path,
    original_log: str,
    local_log: str,
    message: str,
    respect_handled_period: bool,
) -> tuple[str, bool]:
    """Sync scaffold paths while merging the append-only recurring ledger."""
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return original_log, True

    root = _git_toplevel(anchor_path)
    if root is None:
        sys.stderr.write(f"[git] not a git repo (sync skipped): {message}\n")
        return original_log, True

    try:
        rels = [_relative_to_root(root, path) for path in paths]
        log_rel = _relative_to_root(root, template_log)
        template_ticket_rel = _relative_to_root(root, template_log.parent / "ticket.md")
        branch = _current_branch(root)

        try:
            _fetch_control_branch(cfg, root)
        except git.GitError:
            template_log.write_text(local_log)
            git.sync_paths(cfg, anchor_path, paths, message=message)
            return original_log, True
        base = _rev_parse(root, "FETCH_HEAD")
        task_rel = _relative_to_root(root, anchor_path)
        if _control_already_has_period(
            root,
            base,
            log_rel,
            task_rel,
            include_ledger=respect_handled_period,
        ):
            if branch == cfg.git_control_branch:
                _restore_selected_paths_from_ref(root, "HEAD", rels)
                _rebase_checked_out_branch_onto(root, base)
                return (
                    _control_log_with_local_debug(root, "HEAD", log_rel, original_log),
                    False,
                )
            _restore_selected_paths_from_ref(root, base, rels)
            if branch != "HEAD":
                git._commit_paths(root, rels, message)
                return (
                    _control_log_with_local_debug(root, "HEAD", log_rel, original_log),
                    False,
                )
            return (
                _control_log_with_local_debug(root, base, log_rel, original_log),
                False,
            )
        _write_merged_log_for_ref(root, template_log, log_rel, base, local_log)

        if branch == cfg.git_control_branch:
            return _sync_recurring_scaffold_on_checked_out_control_branch(
                cfg,
                root,
                rels,
                template_log=template_log,
                log_rel=log_rel,
                template_ticket_rel=template_ticket_rel,
                original_log=original_log,
                local_log=local_log,
                message=message,
                respect_handled_period=respect_handled_period,
            )

        committed_log = template_log.read_text()
        if branch == "HEAD":
            sys.stderr.write(
                f"[git] detached HEAD — task state landed on "
                f"{cfg.git_control_branch!r} but not committed locally. ({message})\n"
            )
        else:
            git._commit_paths(root, rels, message)
            committed_log = _show_path(root, "HEAD", log_rel)
        landed, already_handled = _land_recurring_scaffold_on_control_branch(
            cfg,
            root,
            rels,
            template_log=template_log,
            log_rel=log_rel,
            template_ticket_rel=template_ticket_rel,
            task_rel=task_rel,
            local_log=local_log,
            message=message,
            respect_handled_period=respect_handled_period,
        )
        if already_handled:
            _restore_selected_paths_from_ref(root, landed, rels)
            if branch != "HEAD":
                git._commit_paths(root, rels, message)
                return (
                    _control_log_with_local_debug(root, "HEAD", log_rel, original_log),
                    False,
                )
            return (
                _control_log_with_local_debug(root, landed, log_rel, original_log),
                False,
            )
        return _merge_log_entries(committed_log, original_log), True
    except git.GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        _append_sync_failure(anchor_path, exc)
        return original_log, True


def _without_debug_log_entries(text: str) -> str:
    """Return log text without local-only `relay recurring --all` debug lines."""
    return "".join(
        line for line in text.splitlines(keepends=True) if not is_debug_slug(line)
    )


def _debug_log_entries(text: str) -> str:
    """Return only local-only `relay recurring --all` debug lines."""
    return "".join(
        line for line in text.splitlines(keepends=True) if is_debug_slug(line)
    )


def _control_log_with_local_debug(
    root: Path, ref: str, log_rel: str, original_log: str
) -> str:
    return _merge_log_entries(
        _show_path(root, ref, log_rel), _debug_log_entries(original_log)
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


def _land_recurring_scaffold_on_control_branch(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    template_log: Path,
    log_rel: str,
    template_ticket_rel: str,
    task_rel: str,
    local_log: str,
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
            log_rel,
            task_rel,
            include_ledger=respect_handled_period,
        ):
            return base, True
        _write_merged_log_for_ref(root, template_log, log_rel, base, local_log)
        control_rels = _control_scaffold_rels(root, base, rels, template_ticket_rel)

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


def _sync_recurring_scaffold_on_checked_out_control_branch(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    template_log: Path,
    log_rel: str,
    template_ticket_rel: str,
    original_log: str,
    local_log: str,
    message: str,
    respect_handled_period: bool,
) -> tuple[str, bool]:
    landed, already_handled = _land_recurring_scaffold_on_control_branch(
        cfg,
        root,
        rels,
        template_log=template_log,
        log_rel=log_rel,
        template_ticket_rel=template_ticket_rel,
        task_rel=rels[0],
        local_log=local_log,
        message=message,
        respect_handled_period=respect_handled_period,
    )
    if already_handled:
        _restore_selected_paths_from_ref(root, "HEAD", rels)
        _rebase_checked_out_branch_onto(root, landed)
        git._push_control_branch(cfg, root)
        return _control_log_with_local_debug(root, "HEAD", log_rel, original_log), False

    _restore_selected_paths_from_ref(root, "HEAD", rels)
    _rebase_checked_out_branch_onto(root, landed)
    git._push_control_branch(cfg, root)
    return _merge_log_entries(_show_path(root, "HEAD", log_rel), original_log), True


def _control_scaffold_rels(
    root: Path, ref: str, rels: list[str], template_ticket_rel: str
) -> list[str]:
    if _ref_has_path(root, ref, template_ticket_rel):
        return rels
    return rels[:1]


def _control_already_has_period(
    root: Path,
    ref: str,
    log_rel: str,
    task_rel: str,
    *,
    include_ledger: bool = True,
) -> bool:
    if _ref_has_path(root, ref, task_rel):
        return True
    if not include_ledger:
        return False
    slug = Path(task_rel).name
    needle = f"scaffolded {slug}"
    return any(
        line.rstrip().endswith(needle)
        for line in _show_path(root, ref, log_rel).splitlines()
    )


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
        _merge_log_entries(_without_debug_log_entries(control_log), local_log)
    )


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
    cfg: Config, ref: TaskRef, *, interactive: bool
) -> None:
    """Stop a bare recurring sweep if one launched task is still in flight.

    `interactive` is set when the sweep is `--interactive` (or the just-
    launched template's own `mode:` was interactive). In that case the human
    is driving — exiting the agent without marking done is a valid "park this
    run and move on" signal, not a stuck task. Make that durable by pausing the
    task, then continue instead of bailing the sweep; otherwise the next scan
    would treat the leftover `in_progress` state as a dead supervisor's orphan
    and relaunch it.
    """
    if not (ref.path / "ticket.md").exists():
        return

    ticket = read_ticket(ref)
    if ticket.status in {"done", "paused"}:
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


def _recurring_idle_timeout() -> float | None:
    """Idle-timeout (seconds) for interactive REPLs the sweep spawns.

    Defaults to `_RECURRING_IDLE_TIMEOUT_SECONDS`; `RELAY_REPL_IDLE_TIMEOUT`
    overrides the window. A `<= 0`, non-finite (`inf`/`nan`), or unparseable
    value disarms the backstop (returns None). Read-only — the value is passed
    explicitly to `relay launch`, never written back to the environment, so it
    cannot leak into the process or a spawned child.
    """
    raw = os.environ.get("RELAY_REPL_IDLE_TIMEOUT")
    if raw is None:
        return _RECURRING_IDLE_TIMEOUT_SECONDS
    try:
        seconds = float(raw)
    except ValueError:
        return None
    if not math.isfinite(seconds) or seconds <= 0:
        return None
    return seconds


def _broadcast_scan(cfg, scan: DueScan) -> None:
    """Post Slack lines for newly scaffolded tasks and skipped templates."""
    for task in list(scan.tasks):
        if not task.created:
            continue
        created_on_control = _sync_recurring_scaffold(cfg, task.template, task.ref)
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
            # The period was scaffolded earlier this cycle and the task
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
