"""Compact the local audit log while preserving events appended during planning."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Callable

from coga.atomicio import atomic_write_bytes
from coga.blackboard import append_blackboard_report
from coga.config import Config, ConfigError, load_config
from coga.log_retention import RetentionError, RetentionSnapshot, cutoff_at, select
from coga.logfile import replace_log
from coga.movement_cursor import MovementError, _state, migrate, movements, replace_state
from coga.paths import log_path, packaged_template_path, recurring_dir, symlink_component, tasks_dir
from coga.recurring_state import CARRIER, INCOMPLETE, parent_state_path, inspect_parent_dir
from coga.runner import run_reported
from coga.task_env import blackboard_from_env
from coga.taskfile import TaskFileError, read_blackboard, replace_blackboard
from coga.tasks import DuplicateTaskSlugError, list_tasks, read_ticket
from coga.ticket import TicketError


_LEGACY_INSTALL_FILES = (
    ("recurring/trim-log/ticket.md", "recurring/trim-log/ticket.md"),
    ("recurring/trim-log/ticket.py", "recurring/trim-log/ticket.py"),
    ("recurring/trim-log/operations.md", "recurring/trim-log/operations.md"),
    ("workflows/trim-log/run.md", "bootstrap/workflows/trim-log/run.md"),
)


def _report(cfg: Config, text: str) -> None:
    path = blackboard_from_env(cfg.repo_root)
    if path is None:
        raise RetentionError("trim-log requires COGA_TASK_BLACKBOARD and COGA_TASK_SLUG")
    append_blackboard_report(cfg, path, "## Trim log\n\n" + text + "\n")


def _phone_compatible(cfg: Config, parent: Path | None) -> tuple[Path, bytes] | None:
    # Parent discovery includes parked installations: stopped reporting still
    # owns unread movement. Two parents or a full local fork need adaptation.
    if parent is not None:
        shim = parent.with_name("ticket.py")
        stock = packaged_template_path("recurring", "phone-home", "ticket.py")
        stock_bytes = stock.read_bytes()
        if symlink_component(parent) is not None:
            raise RetentionError("symlinked phone-home parent needs review before trimming")
        state = inspect_parent_dir(parent.parent)
        if state.kind == INCOMPLETE:
            raise RetentionError(state.problem)
        if state.kind == CARRIER:
            # A state-only carrier selects the packaged definition, whose
            # shim is the stock script by construction. A carrier never
            # inherits a local script: `inspect_parent_dir` reports one
            # beside it as an incomplete fork, refused here as well.
            if shim.exists() or shim.is_symlink():
                raise RetentionError("phone-home carrier has a stray local ticket.py (incomplete fork); make it a full override or remove the script, preserving period_state")
        elif symlink_component(shim) is not None or not shim.is_file() or shim.read_bytes() != stock_bytes:
            raise RetentionError("phone-home local fork is incompatible with trim-log; adapt its cursor or restore the reviewed shim, preserving period_state")
        period_shim = tasks_dir(cfg) / "recurring/phone-home/ticket.py"
        if period_shim.exists() and (symlink_component(period_shim) is not None or period_shim.read_bytes() != stock_bytes):
            raise RetentionError("the frozen phone-home period uses an incompatible fork; adapt that script while preserving period state")
        return stock, stock_bytes
    return None


def trim(cfg: Config, *, clock: Callable[[], date] = date.today) -> str:
    """Select expired events from the local log and replace it atomically."""
    if not cfg.log_retention_days:
        return "Skipped: retention_days = 0; history unchanged."
    path = log_path(cfg)
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return "No audit history to trim."
    if not raw:
        return "No audit history to trim."

    refs = list_tasks(cfg)
    for ref in refs:
        if symlink_component(ref.ticket_path) is not None:
            raise RetentionError(f"symlinked task inventory: {ref.id_slug}")
        read_ticket(ref)
    parent = parent_state_path(cfg, "phone-home")
    unread: set[str] = set()
    migrated_region = None
    if parent.is_file():
        _phone_compatible(cfg, parent)
        region = read_blackboard(parent)
        old_state, _ = _state(region)
        state, _ = migrate(raw, old_state)
        if state["repo_id"] is not None:
            unread = movements(raw) - set(state["seen_movements"])
        if old_state["schema"] == 1:
            migrated_region = replace_state(region, state)

    snapshot = RetentionSnapshot(frozenset(ref.id_slug for ref in refs), frozenset(unread))
    plan = select(raw, snapshot, cutoff_at(clock(), cfg.log_retention_days))
    if not plan.mutation.removed:
        return "No expired unprotected events; history unchanged."
    if migrated_region is not None:
        replace_blackboard(parent, migrated_region)
    replace_log(cfg, plan.mutation)
    kept = len(plan.mutation.postimage)
    removed = len(plan.mutation.removed)
    return (
        f"Removed {removed} events / {len(raw) - kept} bytes. "
        f"Retained {len(plan.events) - removed} events / {kept} bytes. "
        f"Preservation counts/bytes: {plan.summary}."
    )


def run_trim_log(cfg: Config, argv: list[str]) -> int:
    if argv or not os.environ.get("COGA_TASK_SLUG") or blackboard_from_env(cfg.repo_root) is None:
        raise RetentionError("trim-log takes no arguments and requires the period task environment")
    try:
        result = trim(cfg)
    except (RetentionError, MovementError, TicketError, ConfigError, DuplicateTaskSlugError, TaskFileError, UnicodeError, OSError) as exc:
        _report(cfg, "Trim failed: " + str(exc))
        print(str(exc), file=sys.stderr)
        return 2
    _report(cfg, result)
    return 0


def install(cfg: Config) -> list[Path]:
    if (recurring_dir(cfg) / "_trim-log").exists() or (recurring_dir(cfg) / "_trim-log").is_symlink():
        raise RetentionError("_trim-log is parked; review before enabling; no files installed")
    parent = inspect_parent_dir(recurring_dir(cfg) / "trim-log")
    if parent.kind == INCOMPLETE:
        raise RetentionError(parent.problem)
    planned: dict[Path, bytes] = {}
    for rel, packaged in _LEGACY_INSTALL_FILES:
        path = cfg.repo_root / rel
        if path == parent.ticket_path and parent.kind == CARRIER:
            continue
        data = packaged_template_path(*packaged.split("/")).read_bytes()
        if symlink_component(path) is not None or (path.exists() and (not path.is_file() or path.read_bytes() != data)):
            raise RetentionError(f"custom or symlinked {rel}; review before installation; no files installed")
    from coga.recurring import RecurringError, jobs_file_path, planned_job_selection, read_job_selection
    try:
        if read_job_selection(cfg).get("trim-log") is False:
            raise RetentionError(f"trim-log is disabled in {jobs_file_path(cfg)}; review that choice before enabling; no files installed")
        selection = planned_job_selection(cfg, "trim-log", True)
    except RecurringError as exc:
        raise RetentionError(f"{exc}; no files installed") from exc
    if selection is not None:
        if symlink_component(jobs_file_path(cfg)) is not None:
            raise RetentionError("symlinked recurring/jobs.toml needs review; no files installed")
        planned[jobs_file_path(cfg)] = selection
    for path, data in planned.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(path, data)
    return list(planned)
def main() -> int:
    cfg = load_config()
    if sys.argv[1:] == ["--install"]:
        try:
            changed = install(cfg)
        except (RetentionError, OSError) as exc:
            print(f"trim-log adoption: {exc}", file=sys.stderr)
            return 2
        print("trim-log adoption: " + (", ".join(str(p) for p in changed) if changed else "already installed; no changes"))
        return 0
    code = run_reported(cfg, "trim-log", run_trim_log, sys.argv[1:])
    if code:
        return code
    return subprocess.run([sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
