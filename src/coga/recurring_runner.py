"""Recurring scan and launch orchestration shared by command heads and scripts."""

from __future__ import annotations

import json
import math
import os
import subprocess
import shutil
import sys
from datetime import datetime
from pathlib import Path

import typer

from coga import git
from coga.commands.launch import _interactive_stdio_has_tty
from coga.config import Config
from coga.logfile import append_log, ref_tag_for_path, task_log_lines
from coga.paths import log_path
from coga.taskfile import read_blackboard
from coga.recurring import (
    DueTask,
    DueScan,
    RecurringError,
    Template,
    merge_last_serviced_period_text,
    read_last_serviced_period,
    recurring_dir,
    create_named,
    scan_due,
    set_last_serviced_period_text,
    write_last_serviced_period,
)
from coga.period_state import SNAPSHOT_FILE, parse_keys
from coga.mark import mark_active, mark_paused
from coga.notification import notify
from coga.tasks import TaskRef, read_ticket
from coga.ticket import Ticket, TicketError
from coga.validate import TaskValidationError

# Default idle-timeout backstop (seconds) the sweep arms on the interactive
# REPLs it spawns: one that stalls or crashes before signalling done would
# otherwise block the sequential sweep forever — the hang this command was seen
# to hit. Generous enough that a slow-but-progressing agent (which streams PTY
# output) never trips it; only a genuinely silent REPL does. `--interactive`
# (a human driving by hand) leaves it off; `COGA_REPL_IDLE_TIMEOUT` overrides
# the window or, at `<= 0` / non-finite, disarms it.
_RECURRING_IDLE_TIMEOUT_SECONDS = 900.0


def run_recurring_scan(
    cfg: Config, *, force: bool = False, interactive: bool = False
) -> int:
    """Scan every recurring template and launch any due tasks, sequentially.

    Bare `coga recurring` is the default action. For each template under
    `coga/recurring/` it get-or-creates the current period's task, then
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
    `done`/`paused` ones (`coga launch` re-activates them). Everything else —
    Slack, the digest spool, git task-state sync, the `last_serviced_period`
    high-water advance — is identical to a normal run.

    `coga recurring launch <name>` force-runs one named template now.
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

    # `force` launches every materialized task regardless of status;
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


def run_recurring_named(
    cfg: Config, name: str, *, interactive: bool = False
) -> int:
    """Create a named recurring template now and launch it.

    Ignores the template's schedule — the on-demand entry point behind
    aliases like `coga dream`. The task slug is the stable qualified
    `recurring/<name>`, so this and a bare `coga recurring` converge on one
    instantiated task directory.
    """
    try:
        outcome = create_named(cfg, name)
    except RecurringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return 2

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


def _sync_recurring_create(
    cfg: Config,
    template_name: str,
    ref: TaskRef,
    *,
    respect_handled_period: bool = True,
    respect_existing_task: bool = True,
    restore_existing_control_task: bool = False,
    overwrite_dirty_control_task: bool = False,
    force_period_key: str | None = None,
    force_snapshot_is_fresh: bool = False,
    force_record_period: bool = False,
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
    # Single-file format: the template's working state (the `last_serviced_period`
    # high-water line) lives in the blackboard region of its `ticket.md`. There is
    # no per-template `log.md` to merge anymore — period history is appended to the
    # repo-global, union-merged `coga/log.md` (by `_record_run`), which never
    # rides the cross-branch overlay. So the only cross-branch state this sync
    # reconciles is the template ticket.md's high-water mark.
    template_ticket = template_dir / "ticket.md"
    original_ticket = template_ticket.read_text() if template_ticket.is_file() else ""
    local_ticket = original_ticket
    period_key = read_last_serviced_period(template_ticket)
    state_keys: list[str] = []
    if force_period_key is not None:
        try:
            template = Template.load(template_dir)
        except RecurringError:
            template = None
        if template is not None:
            state_keys = list(template.frontmatter.get("state_keys") or [])
    restore_ticket = original_ticket
    created_on_control = True
    try:
        (
            restore_ticket,
            created_on_control,
        ) = _sync_recurring_create_paths(
            cfg,
            anchor_path=ref.path,
            paths=[ref.path, template_ticket],
            template_ticket=template_ticket,
            original_ticket=original_ticket,
            local_ticket=local_ticket,
            period_key=period_key,
            message=message,
            respect_handled_period=respect_handled_period,
            respect_existing_task=respect_existing_task,
            restore_existing_control_task=restore_existing_control_task,
            overwrite_dirty_control_task=overwrite_dirty_control_task,
            force_period_key=force_period_key,
            force_snapshot_is_fresh=force_snapshot_is_fresh,
            force_record_period=force_record_period,
            state_keys=state_keys,
        )
    finally:
        if restore_ticket:
            template_ticket.write_text(restore_ticket)
    return created_on_control


def _sync_recurring_create_paths(
    cfg: Config,
    *,
    anchor_path: Path,
    paths: list[Path],
    template_ticket: Path,
    original_ticket: str,
    local_ticket: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
    respect_existing_task: bool,
    restore_existing_control_task: bool,
    overwrite_dirty_control_task: bool,
    force_period_key: str | None,
    force_snapshot_is_fresh: bool,
    force_record_period: bool,
    state_keys: list[str],
) -> tuple[str, bool]:
    """Sync create paths while merging the template ticket's high-water mark.

    The cross-branch overlay carries the period task dir and the template
    `ticket.md` (`rels`). The repo-global `coga/log.md` is union-merged and
    rides only the *local* commit (`_local_commit_rels`), never the overlay —
    mirroring `coga.git.sync_paths`.
    """
    if not cfg.git_enabled:
        sys.stderr.write(f"[git] disabled (sync suppressed): {message}\n")
        return original_ticket, True

    root = _git_toplevel(anchor_path)
    if root is None:
        sys.stderr.write(f"[git] not a git repo (sync skipped): {message}\n")
        return original_ticket, True

    try:
        rels = [_relative_to_root(root, path) for path in paths]
        ticket_rel = _relative_to_root(root, template_ticket)
        local_rels = _local_commit_rels(cfg, root, rels)
        branch = _current_branch(root)

        try:
            _fetch_control_branch(cfg, root)
        except git.GitError:
            if local_ticket:
                template_ticket.write_text(local_ticket)
            git.sync_paths(cfg, anchor_path, paths, message=message)
            return original_ticket, True
        base = _rev_parse(root, "FETCH_HEAD")
        task_rel = _relative_to_root(root, anchor_path)
        restored_control_task = False
        restored_snapshot: str | None = None
        if restore_existing_control_task:
            restored_control_task, restored_snapshot = _restore_control_task_if_present(
                root,
                base,
                task_rel,
                preserve_local_changes=not overwrite_dirty_control_task,
            )
            if restored_control_task and force_period_key is not None:
                local_ticket, period_key = (
                    _reconcile_forced_period_after_control_restore(
                        cfg,
                        root,
                        base,
                        task_rel=task_rel,
                        ticket_rel=ticket_rel,
                        template_ticket=template_ticket,
                        task_id_slug=_task_id_slug_from_rel(task_rel),
                        force_period_key=force_period_key,
                        snapshot_text_is_fresh=force_snapshot_is_fresh,
                        snapshot_text=restored_snapshot,
                        snapshot_ticket_text=local_ticket,
                        record_period=force_record_period,
                        state_keys=state_keys,
                    )
                )
                original_ticket = local_ticket
                if not force_record_period:
                    return local_ticket, False
        if _control_already_has_period(
            root,
            base,
            ticket_rel,
            task_rel,
            period_key=period_key,
            include_ledger=respect_handled_period,
            include_task=respect_existing_task,
        ):
            if branch == cfg.git_control_branch:
                _restore_selected_paths_from_ref(root, "HEAD", rels)
                _rebase_checked_out_branch_onto(root, base)
                # The create appended to the global log before the sync detected
                # the period was already handled on control; commit that line so
                # the control checkout is left clean (the overlay never carries
                # the log).
                _commit_global_log(cfg, root, message)
                return (
                    _control_blackboard_with_local_period(
                        root, "HEAD", ticket_rel, original_ticket
                    ),
                    False,
                )
            _restore_selected_paths_from_ref(root, base, rels)
            if branch != "HEAD":
                git._commit_paths(root, local_rels, message)
                return (
                    _control_blackboard_with_local_period(
                        root, "HEAD", ticket_rel, original_ticket
                    ),
                    False,
                )
            return (
                _control_blackboard_with_local_period(
                    root, base, ticket_rel, original_ticket
                ),
                False,
            )
        _write_merged_blackboard_for_ref(
            root, template_ticket, ticket_rel, base, local_ticket
        )

        if branch == cfg.git_control_branch:
            return _sync_recurring_create_on_checked_out_control_branch(
                cfg,
                root,
                rels,
                template_ticket=template_ticket,
                ticket_rel=ticket_rel,
                original_ticket=original_ticket,
                local_ticket=local_ticket,
                period_key=period_key,
                message=message,
                respect_handled_period=respect_handled_period,
                respect_existing_task=respect_existing_task,
                restore_existing_control_task=restore_existing_control_task,
                overwrite_dirty_control_task=overwrite_dirty_control_task,
                force_period_key=force_period_key,
                force_snapshot_is_fresh=force_snapshot_is_fresh,
                force_record_period=force_record_period,
                state_keys=state_keys,
            )

        committed_ticket = template_ticket.read_text()
        # Detached HEAD skips the local commit (it would be orphaned); the
        # landing push below fast-forwards the local control ref best-effort
        # via `git._try_update_local_ref`, which reports any miss to stderr.
        if branch != "HEAD":
            git._commit_paths(root, local_rels, message)
            committed_ticket = _show_path(root, "HEAD", ticket_rel)
        landed, already_handled = _land_recurring_create_on_control_branch(
            cfg,
            root,
            rels,
            template_ticket=template_ticket,
            ticket_rel=ticket_rel,
            task_rel=task_rel,
            local_ticket=local_ticket,
            period_key=period_key,
            message=message,
            respect_handled_period=respect_handled_period,
            respect_existing_task=respect_existing_task,
            restore_existing_control_task=restore_existing_control_task,
            overwrite_dirty_control_task=overwrite_dirty_control_task,
            force_period_key=force_period_key,
            force_snapshot_is_fresh=force_snapshot_is_fresh,
            force_record_period=force_record_period,
            state_keys=state_keys,
        )
        if already_handled:
            _restore_selected_paths_from_ref(root, landed, rels)
            if branch != "HEAD":
                git._commit_paths(root, local_rels, message)
                return (
                    _control_blackboard_with_local_period(
                        root, "HEAD", ticket_rel, original_ticket
                    ),
                    False,
                )
            return (
                _control_blackboard_with_local_period(
                    root, landed, ticket_rel, original_ticket
                ),
                False,
            )
        return (
            merge_last_serviced_period_text(committed_ticket, original_ticket),
            True,
        )
    except git.GitError as exc:
        sys.stderr.write(f"[git] sync failed: {exc}. Message was: {message}\n")
        _append_sync_failure(cfg, anchor_path, exc)
        return original_ticket, True


def _local_commit_rels(cfg: Config, root: Path, rels: list[str]) -> list[str]:
    """The overlay `rels` plus the repo-global log for the *local* commit only.

    The global `coga/log.md` is `merge=union`, so it must never ride the
    cross-branch overlay (which replaces files wholesale). It is committed
    locally and reaches control via the same-branch push / PR merge.
    """
    log_file = log_path(cfg)
    if not log_file.exists():
        return rels
    log_rel = _relative_to_root(root, log_file)
    return rels if log_rel in rels else [*rels, log_rel]


def _commit_global_log(cfg: Config, root: Path, message: str) -> None:
    """Commit only the repo-global `coga/log.md`, if it has changes.

    The union-merge global log rides the *local* commit and never the
    cross-branch overlay, so every control-branch return path that may have left
    an appended log line in the working tree (a recurring create that the sync
    then detected was already handled on control, and unwound the task/ticket
    for) must commit it — otherwise the tree is left dirty. A no-op when the log
    is unchanged or the period task path was removed (only the log rel is
    passed, so a removed-task pathspec can't abort the commit)."""
    log_file = log_path(cfg)
    if log_file.exists():
        git._commit_paths(root, [_relative_to_root(root, log_file)], message)


def _control_blackboard_with_local_period(
    root: Path, ref: str, ticket_rel: str, original_ticket: str
) -> str:
    """The control template `ticket.md`, with the local high-water mark merged
    in (take-max). Operates on the whole ticket text; only the
    `last_serviced_period` line is touched."""
    return merge_last_serviced_period_text(
        _show_path(root, ref, ticket_rel), original_ticket
    )


def _append_sync_failure(cfg: Config, anchor_path: Path, exc: Exception) -> None:
    """Best-effort global-log note for non-fatal git sync failures."""
    if not anchor_path.is_dir():
        return
    try:
        append_log(cfg, ref_tag_for_path(cfg, anchor_path), "git", f"sync failed: {exc}")
    except OSError:
        return


def _land_recurring_create_on_control_branch(
    cfg: Config,
    root: Path,
    rels: list[str],
    *,
    template_ticket: Path,
    ticket_rel: str,
    task_rel: str,
    local_ticket: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
    respect_existing_task: bool,
    restore_existing_control_task: bool,
    overwrite_dirty_control_task: bool,
    force_period_key: str | None,
    force_snapshot_is_fresh: bool,
    force_record_period: bool,
    state_keys: list[str],
) -> tuple[str, bool]:
    remote = cfg.git_remote
    branch = cfg.git_control_branch

    for _ in range(git._MAX_SYNC_ATTEMPTS):
        _fetch_control_branch(cfg, root)
        base = _rev_parse(root, "FETCH_HEAD")
        restored_control_task = False
        restored_snapshot: str | None = None
        if restore_existing_control_task:
            restored_control_task, restored_snapshot = _restore_control_task_if_present(
                root,
                base,
                task_rel,
                preserve_local_changes=not overwrite_dirty_control_task,
            )
            if restored_control_task and force_period_key is not None:
                local_ticket, period_key = (
                    _reconcile_forced_period_after_control_restore(
                        cfg,
                        root,
                        base,
                        task_rel=task_rel,
                        ticket_rel=ticket_rel,
                        template_ticket=template_ticket,
                        task_id_slug=_task_id_slug_from_rel(task_rel),
                        force_period_key=force_period_key,
                        snapshot_text_is_fresh=force_snapshot_is_fresh,
                        snapshot_text=restored_snapshot,
                        snapshot_ticket_text=local_ticket,
                        record_period=force_record_period,
                        state_keys=state_keys,
                    )
                )
        if _control_already_has_period(
            root,
            base,
            ticket_rel,
            task_rel,
            period_key=period_key,
            include_ledger=respect_handled_period,
            include_task=respect_existing_task,
        ):
            return base, True
        _write_merged_blackboard_for_ref(
            root, template_ticket, ticket_rel, base, local_ticket
        )
        control_rels = _control_create_rels(root, base, rels, ticket_rel)

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
    template_ticket: Path,
    ticket_rel: str,
    original_ticket: str,
    local_ticket: str,
    period_key: str | None,
    message: str,
    respect_handled_period: bool,
    respect_existing_task: bool,
    restore_existing_control_task: bool,
    overwrite_dirty_control_task: bool,
    force_period_key: str | None,
    force_snapshot_is_fresh: bool,
    force_record_period: bool,
    state_keys: list[str],
) -> tuple[str, bool]:
    landed, already_handled = _land_recurring_create_on_control_branch(
        cfg,
        root,
        rels,
        template_ticket=template_ticket,
        ticket_rel=ticket_rel,
        task_rel=rels[0],
        local_ticket=local_ticket,
        period_key=period_key,
        message=message,
        respect_handled_period=respect_handled_period,
        respect_existing_task=respect_existing_task,
        restore_existing_control_task=restore_existing_control_task,
        overwrite_dirty_control_task=overwrite_dirty_control_task,
        force_period_key=force_period_key,
        force_snapshot_is_fresh=force_snapshot_is_fresh,
        force_record_period=force_record_period,
        state_keys=state_keys,
    )
    _restore_selected_paths_from_ref(root, "HEAD", rels)
    _rebase_checked_out_branch_onto(root, landed)
    # The overlay already landed (and the rebase pulled in) the task dir +
    # template ticket; the only thing still uncommitted is the repo-global
    # `coga/log.md` (union-merge, excluded from the overlay, appended by
    # `_record_run`). Commit just that file so origin and the local control
    # branch reflect the history line and the tree is left clean.
    _commit_global_log(cfg, root, message)
    git._push_control_branch(cfg, root)
    if already_handled:
        return (
            _control_blackboard_with_local_period(
                root, "HEAD", ticket_rel, original_ticket
            ),
            False,
        )
    return (
        merge_last_serviced_period_text(
            _show_path(root, "HEAD", ticket_rel), original_ticket
        ),
        True,
    )


def _control_create_rels(
    root: Path, ref: str, rels: list[str], ticket_rel: str
) -> list[str]:
    if _ref_has_path(root, ref, ticket_rel):
        return rels
    return rels[:1]


def _control_already_has_period(
    root: Path,
    ref: str,
    ticket_rel: str,
    task_rel: str,
    *,
    period_key: str | None,
    include_ledger: bool = True,
    include_task: bool = True,
) -> bool:
    if include_task and _ref_has_path(root, ref, task_rel):
        return True
    if not include_ledger or period_key is None:
        return False
    serviced = _read_control_last_serviced_period(root, ref, ticket_rel)
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


def _restore_control_task_if_present(
    root: Path, ref: str, task_rel: str, *, preserve_local_changes: bool
) -> tuple[bool, str | None]:
    if not _ref_has_path(root, ref, task_rel):
        return False, None
    if preserve_local_changes and _path_has_local_changes(root, task_rel):
        return False, None
    snapshot = root / task_rel / ".state-snapshot.json"
    snapshot_text = snapshot.read_text() if snapshot.is_file() else None
    _restore_selected_paths_from_ref(root, ref, [task_rel])
    return True, snapshot_text


def _path_has_local_changes(root: Path, rel: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", rel],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return any(not _is_generated_snapshot_status(line, rel) for line in lines)


def _is_generated_snapshot_status(line: str, rel: str) -> bool:
    snapshot_rel = f"{Path(rel).as_posix().rstrip('/')}/.state-snapshot.json"
    path = line[3:].strip()
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    return path == snapshot_rel


def _reconcile_forced_period_after_control_restore(
    cfg: Config,
    root: Path,
    ref: str,
    *,
    task_rel: str,
    ticket_rel: str,
    template_ticket: Path,
    task_id_slug: str,
    force_period_key: str,
    snapshot_text_is_fresh: bool,
    snapshot_text: str | None,
    snapshot_ticket_text: str,
    record_period: bool,
    state_keys: list[str],
) -> tuple[str, str | None]:
    """Recompute forced-run bookkeeping after local task state is current.

    Operates on the template's single-file `ticket.md`; the high-water mark is
    the only mutable cross-branch state, and the forced-reused history line goes
    to the repo-global log.
    """
    control_ticket = _show_path(root, ref, ticket_rel)
    if not record_period:
        template_ticket.write_text(
            _local_blackboard_with_control_period(
                snapshot_ticket_text, control_ticket
            )
        )
        merged = template_ticket.read_text() if template_ticket.is_file() else ""
        return merged, read_last_serviced_period(template_ticket)

    template_ticket.write_text(control_ticket)
    current = read_last_serviced_period(template_ticket)
    if current is None or current < force_period_key:
        write_last_serviced_period(template_ticket, force_period_key)
        _append_forced_reused_log(cfg, template_ticket, task_id_slug, force_period_key)

    snapshot = root / task_rel / SNAPSHOT_FILE
    if snapshot_text is not None and snapshot_text_is_fresh:
        snapshot.write_text(snapshot_text)
    elif state_keys:
        _write_snapshot_from_text(
            root / task_rel,
            Path(task_id_slug).name,
            snapshot_ticket_text,
            state_keys,
        )

    merged = template_ticket.read_text() if template_ticket.is_file() else ""
    return merged, read_last_serviced_period(template_ticket)


def _append_forced_reused_log(
    cfg: Config, template_ticket: Path, task_id_slug: str, period_key: str
) -> None:
    """Record a forced reuse in the repo-global log, tagged `recurring/<name>`,
    idempotently (skip if the same line is already present)."""
    tag = f"recurring/{template_ticket.parent.name}"
    needle = f"reused {task_id_slug} for {period_key}"
    if any(needle in line for line in task_log_lines(cfg, tag)):
        return
    append_log(cfg, tag, "system", needle)


def _local_blackboard_with_control_period(
    local_blackboard: str, control_blackboard: str
) -> str:
    period = _last_serviced_period_from_text(control_blackboard)
    if period is None:
        return local_blackboard
    return set_last_serviced_period_text(local_blackboard, period)


def _write_snapshot_from_text(
    task_dir: Path, parent: str, blackboard_text: str, state_keys: list[str]
) -> None:
    keys = parse_keys(blackboard_text, list(state_keys))
    payload = {"parent": parent, "keys": keys}
    (task_dir / SNAPSHOT_FILE).write_text(json.dumps(payload, indent=2) + "\n")


def _task_id_slug_from_rel(rel: str) -> str:
    parts = Path(rel).parts
    if "tasks" not in parts:
        return Path(rel).name
    i = len(parts) - 1 - list(reversed(parts)).index("tasks")
    return "/".join(parts[i + 1 :])


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


def _write_merged_blackboard_for_ref(
    root: Path,
    template_ticket: Path,
    ticket_rel: str,
    ref: str,
    local_ticket: str,
) -> None:
    """Write the template `ticket.md` with the control + local high-water marks
    merged (take-max). Whole-text merge; only the high-water line changes."""
    control_ticket = _show_path(root, ref, ticket_rel)
    template_ticket.write_text(
        merge_last_serviced_period_text(control_ticket, local_ticket)
    )


def _read_control_last_serviced_period(
    root: Path, ref: str, ticket_rel: str
) -> str | None:
    text = _show_path(root, ref, ticket_rel)
    return _last_serviced_period_from_text(text)


def _last_serviced_period_from_text(text: str) -> str | None:
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


def _refresh_forced_status_from_control(cfg: Config, task: DueTask) -> None:
    """Best-effort read-only status refresh for `--all` launch ordering."""
    if task.ref is None or not cfg.git_enabled:
        return
    root = _git_toplevel(task.ref.path)
    if root is None:
        return
    task_rel = _relative_to_root(root, task.ref.path)
    if _path_has_local_changes(root, task_rel):
        return
    try:
        _fetch_control_branch(cfg, root)
        base = _rev_parse(root, "FETCH_HEAD")
    except git.GitError as exc:
        sys.stderr.write(f"[git] forced status refresh skipped: {exc}\n")
        return
    text = _show_path(root, base, f"{task_rel}/ticket.md")
    if not text:
        return
    try:
        ticket = Ticket.parse(text)
    except TicketError:
        return
    task.status = ticket.status


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
