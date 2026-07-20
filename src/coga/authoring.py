"""Guided ticket-authoring finalization helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from coga import git
from coga.config import Config, load_config
from coga.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    list_tasks,
    read_ticket,
    resolve_bootstrap,
    resolve_task,
)
from coga.validate import assert_task_valid


AUTHORING_SYNC_DIRS = ("tasks", "contexts", "skills")
AUTHORING_REF_ENV = "COGA_AUTHORING_REF"
AUTHORING_SNAPSHOT_ENV = "COGA_AUTHORING_SNAPSHOT"


class AuthoringError(Exception):
    """Raised when post-authoring validation or sync setup fails."""


@dataclass(frozen=True)
class AuthoringSnapshot:
    """The pre-session state needed to finalize a guided authoring run."""

    tasks: frozenset[str]
    files: Mapping[Path, str]


def snapshot_authoring_state(cfg: Config) -> AuthoringSnapshot:
    """Capture task ids and authoring-owned file digests before the session."""
    return AuthoringSnapshot(
        tasks=frozenset(task_ref.id_slug for task_ref in list_tasks(cfg)),
        files=snapshot_authoring_files(cfg),
    )


def snapshot_authoring_files(cfg: Config) -> dict[Path, str]:
    """Hash files the authoring interview is allowed to create or modify."""
    snapshot: dict[Path, str] = {}
    for root_name in AUTHORING_SYNC_DIRS:
        root = cfg.repo_root / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                snapshot[path.resolve(strict=False)] = sha256(
                    path.read_bytes()
                ).hexdigest()
    return snapshot


def changed_authoring_paths(
    before: Mapping[Path, str],
    cfg: Config,
) -> set[Path]:
    """Return created, changed, and deleted authoring-owned paths."""
    after = snapshot_authoring_files(cfg)
    changed = {path for path, digest in after.items() if before.get(path) != digest}
    changed.update(path for path in before if path not in after)
    return changed


def authored_task_refs(
    cfg: Config,
    changed_paths: set[Path],
    before_tasks: set[str] | frozenset[str],
) -> list[TaskRef]:
    """Resolve changed/new task paths to task refs without assuming depth."""
    refs: dict[str, TaskRef] = {}
    tasks = list_tasks(cfg)
    resolved = [path.resolve(strict=False) for path in changed_paths]
    for task_ref in tasks:
        task_root = task_ref.path.resolve(strict=False)
        if any(path == task_root or task_root in path.parents for path in resolved):
            refs[task_ref.id_slug] = task_ref

    for task_ref in tasks:
        if task_ref.id_slug not in before_tasks:
            refs.setdefault(task_ref.id_slug, task_ref)
    return [refs[slug] for slug in sorted(refs)]


def support_paths(cfg: Config, changed_paths: set[Path]) -> list[Path]:
    """Return changed non-task support files authored by the interview."""
    support: list[Path] = []
    for root_name in ("contexts", "skills"):
        root = (cfg.repo_root / root_name).resolve(strict=False)
        for path in changed_paths:
            try:
                path.resolve(strict=False).relative_to(root)
            except ValueError:
                continue
            support.append(path)
    return sorted(support)


def authoring_sync_message(authored_refs: list[TaskRef]) -> str:
    """Commit message for a guided authoring sync."""
    if len(authored_refs) == 1:
        return f"Ticket: {authored_refs[0].id_slug} — authored"
    if authored_refs:
        slugs = ", ".join(ref.id_slug for ref in authored_refs)
        return f"Ticket authoring — authored {slugs}"
    return "Ticket authoring — support files"


def validate_authored_task(cfg: Config, ref: TaskRef) -> None:
    """Validate an authored task and gate workflow-less drafts."""
    assert_task_valid(cfg, ref, action="ticket authoring")

    # Guided authoring of a draft must land on a workflow. A workflow-less
    # draft can't be activated (`coga mark active` refuses it), so handing
    # one back would strand the human. Catch it here, at the terminal,
    # rather than later at activation. Only drafts are gated: an already
    # `active` ticket edited here may be a workflow-less recurring/retire
    # task, which is legitimate.
    authored = read_ticket(ref)
    if authored.status == "draft" and not authored.workflow:
        raise AuthoringError(
            f"Ticket authoring left {ref.id_slug} with no workflow. "
            "Every ticket needs one to be activated — relaunch "
            f"`coga ticket {ref.id_slug}` and pick a workflow "
            "(see coga/workflows/)."
        )


def finalize_authored(
    cfg: Config,
    *,
    before_snapshot: AuthoringSnapshot,
    ref: TaskRef | BootstrapRef,
) -> None:
    """Run post-authoring validation and sync for a completed interview."""
    changed_paths = changed_authoring_paths(before_snapshot.files, cfg)
    task_sync_paths: list[Path]
    if isinstance(ref, TaskRef):
        # The interview may promote a flat task to directory form so it can
        # carry a sibling script. Re-resolve by the shape-independent id_slug:
        # the TaskRef captured before the session still points at the removed
        # `<slug>.md` and would otherwise look like an intentional deletion.
        try:
            authored_ref = resolve_task(cfg, ref.id_slug)
        except TaskNotFoundError:
            # A session may legitimately end by deleting the ticket (the human
            # decides the task should go away — `coga delete` already committed
            # the removal), so there is nothing to validate or re-sync.
            authored_refs = []
            task_sync_paths = []
        else:
            authored_refs = [authored_ref]
            task_sync_paths = [authored_ref.path]
            if authored_ref.path.resolve(strict=False) != ref.path.resolve(
                strict=False
            ):
                # Stage the removed and added sides of the shape conversion.
                task_sync_paths.insert(0, ref.path)
    else:
        authored_refs = authored_task_refs(
            cfg, changed_paths, before_snapshot.tasks
        )
        task_sync_paths = [authored_ref.path for authored_ref in authored_refs]

    for authored_ref in authored_refs:
        validate_authored_task(cfg, authored_ref)

    sync_paths = task_sync_paths
    sync_paths.extend(support_paths(cfg, changed_paths))
    if sync_paths:
        anchor = authored_refs[0].path if authored_refs else cfg.repo_root
        git.sync_paths(
            cfg,
            anchor,
            sync_paths,
            message=authoring_sync_message(authored_refs),
        )


def write_authoring_snapshot(snapshot: AuthoringSnapshot, path: Path) -> None:
    """Write a snapshot file consumable by the script-skill entry point."""
    payload = {
        "tasks": sorted(snapshot.tasks),
        "files": {str(path): digest for path, digest in snapshot.files.items()},
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n")


def load_authoring_snapshot(path: Path) -> AuthoringSnapshot:
    """Read a snapshot file written by `write_authoring_snapshot`."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthoringError(f"failed to read authoring snapshot {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AuthoringError("authoring snapshot must be a JSON object")
    raw_tasks = data.get("tasks", [])
    raw_files = data.get("files", {})
    if not isinstance(raw_tasks, list) or not all(
        isinstance(item, str) for item in raw_tasks
    ):
        raise AuthoringError("authoring snapshot `tasks` must be a list of strings")
    if not isinstance(raw_files, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in raw_files.items()
    ):
        raise AuthoringError("authoring snapshot `files` must map paths to digests")
    return AuthoringSnapshot(
        tasks=frozenset(raw_tasks),
        files={Path(path): digest for path, digest in raw_files.items()},
    )


def resolve_authoring_ref(cfg: Config, value: str) -> TaskRef | BootstrapRef:
    """Resolve a task/bootstrap ref string for the script-skill entry point."""
    if value.startswith("bootstrap/"):
        try:
            return resolve_bootstrap(cfg, value.removeprefix("bootstrap/"))
        except TaskNotFoundError as exc:
            raise AuthoringError(str(exc)) from exc
    try:
        return resolve_task(cfg, value)
    except TaskNotFoundError as exc:
        if str(exc).startswith("Ambiguous task ref"):
            raise AuthoringError(str(exc)) from exc
        try:
            return resolve_bootstrap(cfg, value)
        except TaskNotFoundError as bootstrap_exc:
            raise AuthoringError(str(bootstrap_exc)) from exc


def finalize_authored_from_env(
    cfg: Config | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Finalize authoring using the script-skill environment contract."""
    env = environ if environ is not None else os.environ
    ref_value = env.get(AUTHORING_REF_ENV)
    snapshot_value = env.get(AUTHORING_SNAPSHOT_ENV)
    missing = [
        name
        for name, value in (
            (AUTHORING_REF_ENV, ref_value),
            (AUTHORING_SNAPSHOT_ENV, snapshot_value),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise AuthoringError(f"missing required authoring env var(s): {joined}")

    loaded_cfg = cfg if cfg is not None else load_config()
    snapshot = load_authoring_snapshot(Path(snapshot_value or ""))
    ref = resolve_authoring_ref(loaded_cfg, ref_value or "")
    finalize_authored(loaded_cfg, before_snapshot=snapshot, ref=ref)
