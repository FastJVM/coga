"""Weekly audit maintenance and its bounded, explicit adoption operation."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Callable

from coga import git, log_transaction
from coga.atomicio import atomic_write_bytes
from coga.blackboard import append_blackboard_report
from coga.config import Config, ConfigError, load_config
from coga.log_publication import Inputs, cursor_state, read_inputs, snapshot
from coga.log_retention import RetentionError, cutoff_at, select
from coga.logfile import replace_log
from coga.movement_cursor import MovementError, _state, replace_state
from coga.paths import log_path, packaged_template_path, recurring_dir, tasks_dir
from coga.runner import run_reported
from coga.task_env import blackboard_from_env
from coga.taskfile import TaskFileError, read_blackboard, replace_blackboard
from coga.tasks import DuplicateTaskSlugError, list_tasks, read_ticket
from coga.ticket import TicketError

_INSTALL_FILES = (
    "recurring/trim-log/ticket.md", "recurring/trim-log/ticket.py",
    "recurring/trim-log/operations.md", "workflows/trim-log/run.md",
)


def _report(cfg: Config, text: str) -> None:
    path = blackboard_from_env(cfg.repo_root)
    if path is None:
        raise RetentionError("trim-log requires COGA_TASK_BLACKBOARD and COGA_TASK_SLUG")
    append_blackboard_report(cfg, path, "## Trim log\n\n" + text + "\n")


def _phone_compatible(cfg: Config) -> None:
    # Parent discovery includes parked installations: stopped reporting still
    # owns unread movement. Two parents or a full local fork need adaptation.
    parent = recurring_dir(cfg) / "phone-home/ticket.md"
    parked = recurring_dir(cfg) / "_phone-home"
    if parked.exists():
        raise RetentionError("parked phone-home needs explicit cursor adaptation before trimming; preserve its state")
    if parent.exists():
        shim = parent.with_name("ticket.py")
        stock = packaged_template_path("recurring", "phone-home", "ticket.py")
        if git.symlink_component(parent) is not None or git.symlink_component(shim) is not None or not shim.is_file() or shim.read_bytes() != stock.read_bytes():
            raise RetentionError("phone-home local fork is incompatible with trim-log; adapt its cursor or restore the reviewed shim, preserving period_state")
        period_shim = tasks_dir(cfg) / "recurring/phone-home/ticket.py"
        if period_shim.exists() and (git.symlink_component(period_shim) is not None or period_shim.read_bytes() != stock.read_bytes()):
            raise RetentionError("the frozen phone-home period uses an incompatible fork; adapt that script while preserving period state")


def _local_inputs(
    cfg: Config, root: Path, rev: str, outputs: dict[Path, bytes] | None = None,
) -> Inputs:
    try:
        return _check_local_inputs(cfg, root, rev, outputs or {})
    except OSError as exc:
        raise RetentionError(f"retention inventory is unreadable; repair before trimming: {exc}") from exc


def _check_local_inputs(cfg: Config, root: Path, rev: str, outputs: dict[Path, bytes]) -> Inputs:
    inputs = read_inputs(cfg, root, rev)
    wanted = [cfg.repo_root / "coga.toml", tasks_dir(cfg), recurring_dir(cfg) / "phone-home"]
    expected = {git.relative_to_root(root, p): data for p, data in outputs.items()}
    dirty = set(git._dirty_paths(root, [git.relative_to_root(root, p) for p in wanted])) - expected.keys()
    if dirty:
        raise RetentionError("retention inventory/config/phone-home has unpublished edits; publish or reconcile those edits before trimming")
    # Match actual list_tasks discovery, including all statuses, rather than
    # silently treating an unreadable or duplicate inventory as empty.
    refs = list_tasks(cfg)
    for ref in refs:
        if git.symlink_component(ref.ticket_path) is not None:
            raise RetentionError(f"symlinked task inventory: {ref.id_slug}")
        read_ticket(ref)
    if frozenset(ref.id_slug for ref in refs) != inputs.refs:
        raise RetentionError("local task inventory differs from current control; refresh before trimming")
    for name, mode, oid in inputs.entries:
        local = root / name
        if not local.is_file():
            raise RetentionError(f"retention decision input is missing: {name}")
        raw = local.read_bytes()
        matches = raw == expected[name] if name in expected else git._hash_blob(root, raw, name) == oid
        if not matches:
            raise RetentionError(f"retention decision input differs from current control: {name}")
    _phone_compatible(cfg)
    return inputs


def trim(cfg: Config, *, clock: Callable[[], date] = date.today) -> str:
    """One bounded maintenance transaction; no lifecycle subprocess under lock."""
    if not cfg.git_enabled:
        if log_transaction.pending(cfg):
            raise git.UncertainPublishError("restore Git access before recovering the pending trim")
        return "Skipped: Git disabled; history unchanged."
    root = git.toplevel(cfg.repo_root)
    if root is None:
        return "Skipped: not a Git repository; history unchanged."
    with git.state_lock(cfg):
        recovered = log_transaction.recover(cfg)
        if git.current_branch(root) != cfg.git_control_branch:
            raise RetentionError(f"trim-log requires the managed {cfg.git_control_branch} checkout")
        if not cfg.log_retention_days:
            return "Skipped: retention_days = 0; history unchanged."
        path = log_path(cfg)
        if not path.exists() or not path.read_bytes():
            return "No audit history to trim."
        for attempt in range(3):
            # Pending events must first be recoverable from reachable history.
            try:
                published = git.publish(cfg, [path], "Log: recurring/trim-log — archive pending events", require_paths=[path])
            except git.StateRegressionError as exc:
                if isinstance(exc.__cause__, (ValueError, TicketError, ConfigError)):
                    raise RetentionError(str(exc.__cause__)) from exc
                raise
            if published is None:
                raise git.GitError("pending audit events could not be archived; no trimming performed")
            rev = git.fetch_control(cfg, root)
            if not git.fast_forward_control(cfg, root, rev):
                raise git.GitError("control checkout could not catch up before retention planning")
            raw = path.read_bytes()
            rel = git.relative_to_root(root, path)
            if git._clean_bytes(root, raw, rel) != (git.tree_bytes(root, rev, rel) or b""):
                raise git.GitError("audit log differs from archived control; retry after publication")
            # Git blobs are LF under a clean filter. Keep the working preimage
            # byte-exact; a receipt also checks its clean-filtered control copy.
            inputs = _local_inputs(cfg, root, rev)
            if not inputs.days:
                return "Skipped: control retention_days = 0; history unchanged."
            plan = select(raw, snapshot(inputs, raw), cutoff_at(clock(), inputs.days))
            parent = recurring_dir(cfg) / "phone-home/ticket.md"
            state = cursor_state(inputs.parent, raw)
            parent_before = parent.read_bytes() if inputs.parent is not None else None
            region = read_blackboard(parent, expected_bytes=parent_before) if parent_before is not None else None
            migrated_region = replace_state(region, state) if region is not None and _state(region)[0]["schema"] == 1 else None
            if not plan.mutation.removed:
                return "No expired unprotected events; history unchanged."
            outputs: dict[Path, bytes] = {}
            if migrated_region is not None:
                assert region is not None and inputs.parent is not None
                prefix = parent_before[:-len(region.encode("utf-8"))] if region else parent_before
                outputs[parent] = prefix + migrated_region.encode("utf-8")
            kept = len(raw) - sum(len(plan.events[i].raw) for i in plan.mutation.removed)
            message = f"Log: recurring/trim-log — retained {len(plan.events) - len(plan.mutation.removed)} events / {kept} bytes"
            def guard(base: str) -> None:
                current = read_inputs(cfg, root, base)
                if current.entries != inputs.entries:
                    raise git.StateRegressionError("retention config/task/cursor inputs changed on control; replan")
                _local_inputs(cfg, root, rev, outputs)
            log_transaction.begin(cfg, rev, plan.mutation, outputs, message)
            try:
                if migrated_region is not None:
                    replace_blackboard(parent, migrated_region, expected_bytes=parent_before)
                replace_log(cfg, plan.mutation)
                result = git.publish(
                    cfg, [path, *outputs], message,
                    expect={path: raw, **({parent: inputs.parent} if outputs else {})},
                    guard=guard, require_paths=[path, *outputs], log_mutation=plan.mutation,
                )
                if result is None:
                    raise git.UncertainPublishError("trim publication was skipped; retained receipt requires recovery")
                log_transaction.finish(cfg)
                return (f"Removed {len(plan.mutation.removed)} events / {len(raw) - kept} bytes; "
                        f"retained {len(plan.events) - len(plan.mutation.removed)} events / {kept} bytes. "
                        f"Preservation counts/bytes: {plan.summary}." + (f" Recovery: {recovered}." if recovered else ""))
            except (TaskFileError, OSError) as exc:
                raise git.UncertainPublishError(f"audit replacement interrupted; retain receipt and recover: {exc}") from exc
            except git.UncertainPublishError:
                raise
            except (ValueError, TicketError, ConfigError, DuplicateTaskSlugError):
                log_transaction.recover(cfg)
                raise
            except git.GitError:
                # Fresh remote evidence distinguishes definite refusal from
                # accepted-but-unacknowledged, preserving appended diagnostics.
                log_transaction.recover(cfg)
                if attempt == 2:
                    raise
        raise AssertionError("bounded retry exhausted")


def run_trim_log(cfg: Config, argv: list[str]) -> int:
    if argv or not os.environ.get("COGA_TASK_SLUG") or blackboard_from_env(cfg.repo_root) is None:
        raise RetentionError("trim-log takes no arguments and requires the period task environment")
    try:
        result = trim(cfg)
    except (RetentionError, MovementError, TicketError, ConfigError, DuplicateTaskSlugError, TaskFileError, UnicodeError) as exc:
        _report(cfg, "Prerequisite: " + str(exc))
        return subprocess.run([sys.executable, "-m", "coga.cli", "block", "--task", os.environ["COGA_TASK_SLUG"], "--reason", str(exc)], check=False).returncode or 2
    except (git.GitError, OSError) as exc:
        _report(cfg, "Publication not complete; retained state needs retry/recovery: " + str(exc))
        print(str(exc), file=sys.stderr)
        return git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    _report(cfg, result)
    return 0


def _attribute_plan(cfg: Config, root: Path) -> tuple[Path, bytes]:
    path = cfg.repo_root / ".gitattributes"
    if git.symlink_component(path) is not None:
        raise RetentionError("symlinked .gitattributes needs review")
    raw = path.read_bytes() if path.exists() else b""
    lines = raw.splitlines(keepends=True)
    stock = [i for i, line in enumerate(lines) if line.rstrip(b"\r\n") == b"**/log.md merge=union"]
    target = b"/log.md -merge"
    existing = [i for i, line in enumerate(lines) if line.rstrip(b"\r\n") == target]
    log_rel = git.relative_to_root(root, log_path(cfg))
    effective = git.run_git(root, "check-attr", "merge", "--", log_rel).strip().rsplit(": ", 1)[-1]
    if len(stock) > 1 or len(existing) > 1 or (stock and existing):
        raise RetentionError("conflicting audit attributes need review")
    if stock:
        if effective != "union":
            raise RetentionError("effective audit merge attribute differs from stock; review overrides")
        i = stock[0]
        ending = b"\r\n" if lines[i].endswith(b"\r\n") else b"\n" if lines[i].endswith(b"\n") else b""
        lines[i] = target + ending
        replacement = b"".join(lines)
    elif existing:
        replacement = raw
    elif effective == "unspecified":
        replacement = raw + (b"\n" if raw and not raw.endswith(b"\n") else b"") + target + b"\n"
    else:
        raise RetentionError("unfamiliar audit merge attribute needs review; no files installed")
    # Check the effective proposed rule, including info/global/ancestor rules.
    with tempfile.TemporaryDirectory(prefix="coga-trim-install-") as tmp:
        env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        git.run_git(root, "read-tree", "HEAD", env=env)
        rel = git.relative_to_root(root, path)
        git.run_git(root, "update-index", "--add", "--cacheinfo", "100644", git._hash_blob(root, replacement, rel), rel, env=env)
        proposed = git.run_git(root, "check-attr", "--cached", "merge", "--", log_rel, env=env).strip().rsplit(": ", 1)[-1]
        if proposed != "unset":
            raise RetentionError("effective audit merge attribute would not be -merge; review overriding attributes")
    return path, replacement


def install(cfg: Config) -> list[Path]:
    root = git.toplevel(cfg.repo_root)
    if root is None:
        raise RetentionError("trim-log adoption requires a Git checkout for effective attribute verification")
    with git.state_lock(cfg):
        if (recurring_dir(cfg) / "_trim-log").exists() or (recurring_dir(cfg) / "_trim-log").is_symlink():
            raise RetentionError("_trim-log is parked; review before enabling; no files installed")
        planned: dict[Path, bytes] = {}
        for rel in _INSTALL_FILES:
            path = cfg.repo_root / rel
            data = packaged_template_path(*rel.split("/")).read_bytes()
            if git.symlink_component(path) is not None or (path.exists() and (not path.is_file() or path.read_bytes() != data)):
                raise RetentionError(f"custom or symlinked {rel}; review before installation; no files installed")
            if not path.exists():
                planned[path] = data
        attr, data = _attribute_plan(cfg, root)
        if not attr.exists() or attr.read_bytes() != data:
            planned[attr] = data
        for path, data in planned.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(path, data)
            if path.name == "ticket.py":
                path.chmod(path.stat().st_mode | 0o111)
        return list(planned)


def main() -> int:
    cfg = load_config()
    if sys.argv[1:] == ["--install"]:
        try:
            changed = install(cfg)
        except (RetentionError, git.GitError, OSError) as exc:
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
