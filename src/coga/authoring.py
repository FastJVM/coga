"""Guided ticket-authoring finalization helpers."""

from __future__ import annotations

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
    resolve_task,
)
from coga.validate import assert_task_valid


AUTHORING_SYNC_DIRS = ("tasks", "contexts", "skills")
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
        # carry attachments. Re-resolve by the shape-independent id_slug:
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
