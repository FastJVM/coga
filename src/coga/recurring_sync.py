"""Control-branch reconciliation for recurring creates.

Lifted out of `coga.commands.recurring` so both the bare scan runner
(`coga.recurring_runner`) and the on-demand `recurring launch <name>` path
share one implementation. This is not "scan logic" in the product sense — it is
the git plumbing every recurring create needs to land the period task and the
template's `last_serviced_period` high-water mark on the control branch
idempotently. The semantics are unchanged from when this lived in the command
module: take-max high-water merge, control-branch overlay landing,
feature-only template handling, existing control-task restore, forced-run
snapshot repair, and union-safe global-log handling.
"""

from __future__ import annotations

import json
import subprocess
import shutil
import sys
from pathlib import Path

from coga import git
from coga.config import Config
from coga.logfile import append_log, ref_tag_for_path, task_log_lines
from coga.paths import log_path, recurring_dir
from coga.period_state import SNAPSHOT_FILE, parse_keys
from coga.recurring import (
    DueTask,
    RecurringError,
    Template,
    merge_last_serviced_period_text,
    read_last_serviced_period,
    set_last_serviced_period_text,
    write_last_serviced_period,
)
from coga.tasks import TaskRef
from coga.ticket import Ticket, TicketError


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
        if branch == "HEAD":
            sys.stderr.write(
                f"[git] detached HEAD — task state landed on "
                f"{cfg.git_control_branch!r} but not committed locally. ({message})\n"
            )
        else:
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
