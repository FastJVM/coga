"""Guided ticket-authoring finalization helpers."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from coga import git
from coga.config import Config, ConfigError, find_checkout_root, load_config
from coga.logfile import log_path
from coga.paths import tasks_dir
from coga.tasks import (
    BootstrapRef,
    TaskNotFoundError,
    TaskRef,
    list_tasks,
    read_ticket,
    resolve_task,
)
from coga.ticket import Ticket
from coga.validate import assert_task_valid


# Session-length override for the authoring interview's agent — e.g.
# `export COGA_AUTHORING_AGENT=codex` while a Claude quota is exhausted. Read
# here rather than in `config.py`, like `COGA_REPL_*` over `[launch]`.
AUTHORING_AGENT_ENV = "COGA_AUTHORING_AGENT"


def resolve_authoring_agent(
    cfg: Config,
    *,
    source_ticket: Ticket,
    bootstrap_ticket: Ticket,
    agent_override: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Pick the agent type that runs a ticket-authoring interview.

    Shared by `coga ticket` and megalaunch's picked-draft authoring pass. The
    first non-empty term wins:

    1. `agent_override` (`--agent`, `coga megalaunch --agent`, or the
       `coga ticket --pick-agent` answer);
    2. the `COGA_AUTHORING_AGENT` environment variable;
    3. `[authoring] agent` in coga.local.toml;
    4. the target ticket's own `agent:` (skipped when the target *is* the
       bootstrap ticket, as on a bare `coga ticket`);
    5. `bootstrap/ticket`'s `agent:` — the install-level default;
    6. `Config.default_agent()`, the first declared `[agents.*]` type.

    The winner must name a configured agent type. An unknown or malformed name
    fails loud with the term that supplied it rather than falling through to a
    later term. The choice selects the interviewer only and is never written
    onto the ticket.
    """
    env = os.environ if environ is None else environ
    candidates: list[tuple[object, str]] = [
        (agent_override or None, "--agent"),
        (env.get(AUTHORING_AGENT_ENV) or None, AUTHORING_AGENT_ENV),
        (cfg.authoring_agent or None, "[authoring] agent in coga.local.toml"),
    ]
    if source_ticket is not bootstrap_ticket:
        candidates.append((source_ticket.agent, "the ticket's `agent:`"))
    candidates.append((bootstrap_ticket.agent, "bootstrap/ticket's `agent:`"))
    for value, source in candidates:
        if value is None:
            continue
        hint = "" if source == "--agent" else "; pass --agent <name> to override"
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(
                f"Authoring agent must be a non-empty agent type name, got "
                f"{value!r} (from {source}{hint})."
            )
        name = value.strip()
        try:
            cfg.agent_type(name)
        except ConfigError as exc:
            raise ConfigError(f"{exc} (from {source}{hint})") from exc
        return name
    default = cfg.default_agent()
    if default is None:
        raise ConfigError(
            "No agent types are configured; declare at least one `[agents.*]` "
            "table in coga.toml or coga.local.toml (e.g. `[agents.claude]`)."
        )
    return default.name


def authoring_sync_roots(cfg: Config) -> tuple[Path, ...]:
    """Absolute roots the authoring interview may create or modify files under.

    The same Coga and contexts roots the state sweep publishes
    (`git.coga_root_paths`), resolved off config because `[layout] contexts`
    can move the contexts directory outside the coga root entirely.
    """
    return git.coga_root_paths(cfg)


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
    for path in _authoring_files(cfg):
        # Never turn a link in an authoring root into an explicit publication
        # request for its target (which may be source outside these roots).
        if git.symlink_component(path) is None and path.is_file():
            snapshot[path.absolute()] = sha256(path.read_bytes()).hexdigest()
    return snapshot


def _authoring_files(cfg: Config) -> list[Path]:
    """Files under the authoring roots that publication could carry.

    In a Git checkout, Git lists them (tracked plus unignored untracked), so
    ignored local files such as `coga.local.toml` and generated agent views
    are never hashed, reported, or published. Outside one, every file.
    """
    roots = [root for root in authoring_sync_roots(cfg) if root.is_dir()]
    if not roots:
        return []
    try:
        top = git.toplevel(cfg.repo_root) if find_checkout_root(cfg.repo_root) else None
        if top is not None:
            out = git.run_git(
                top, "ls-files", "-z", "--cached", "--others", "--exclude-standard",
                "--", *(git.relative_to_root(top, root) for root in roots),
                env={"GIT_LITERAL_PATHSPECS": "1"},
            )
            return [top / rel for rel in sorted(set(out.split("\x00"))) if rel]
    except git.GitError:
        pass
    return [path for root in roots for path in sorted(root.rglob("*"))]


def changed_authoring_paths(
    before: Mapping[Path, str],
    cfg: Config,
) -> set[Path]:
    """Return created, changed, and deleted authoring-owned paths."""
    after = snapshot_authoring_files(cfg)
    changed = {path for path, digest in after.items() if before.get(path) != digest}
    # Disappearing from the eligible inventory is not always a deletion: an
    # existing regular file may now be ignored or outside relocated roots.
    # Keep link replacements visible so finalization refuses their targets.
    changed.update(
        path for path in before if path not in after
        and (git.symlink_component(path) is not None or not path.is_file())
    )
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
    """Changed files outside the tasks directory: contexts, skills, workflows, config.

    The audit log is excluded: launch and lifecycle writers own it, and the
    state sweep publishes it.
    """
    tasks_root = tasks_dir(cfg).resolve(strict=False)
    log = log_path(cfg).resolve(strict=False)
    support: list[Path] = []
    for path in changed_paths:
        resolved = path.resolve(strict=False)
        if resolved == log or resolved == tasks_root or tasks_root in resolved.parents:
            continue
        support.append(path)
    return sorted(support)


def authoring_sync_message(authored_refs: list[TaskRef]) -> str:
    """Commit message for a guided authoring sync."""
    if not authored_refs:
        return "Ticket authoring — knowledge edits"
    if len(authored_refs) == 1:
        return f"Ticket: {authored_refs[0].id_slug} — authored"
    slugs = ", ".join(ref.id_slug for ref in authored_refs)
    return f"Ticket authoring — authored {slugs}"


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
    """Validate a completed interview, then publish what it authored.

    Authored task paths and every changed file under the Coga and contexts
    roots outside the tasks directory land together in one guarded publish.
    A refused or failed publish keeps every edit on disk and raises
    `AuthoringError`, so the interview never reports a completed handoff it
    could not make durable.
    """
    try:
        cfg = load_config(cfg.repo_root, require_user=False)
    except ConfigError as exc:
        raise AuthoringError(f"Authored configuration is invalid: {exc}") from exc
    # Use the new roots for discovery and validation, but keep the original
    # snapshot so a relocation publishes its old-path deletions atomically
    # with the new files and configuration.
    changed_paths = changed_authoring_paths(before_snapshot.files, cfg)
    for path in sorted(changed_paths):
        if git.symlink_component(path) is not None:
            raise AuthoringError(
                f"Authored path {path} is a symlink or has a symlinked ancestor; "
                "replace it with regular files before publication. Edits are kept on disk."
            )
    support = support_paths(cfg, changed_paths)

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
            task_root = authored_ref.path.resolve(strict=False)
            task_sync_paths = (
                [authored_ref.path]
                if any(
                    path == task_root or task_root in path.parents
                    for path in changed_paths
                )
                else []
            )
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

    sync_paths = [*task_sync_paths, *support]
    if not sync_paths:
        return
    try:
        published = git.publish(
            cfg, sync_paths, authoring_sync_message(authored_refs), require_paths=support,
        )
    except git.GitError as exc:
        raise AuthoringError(
            f"Authored changes were not published: {exc}. They are kept on "
            "disk as written; the next Coga command's state sweep retries them."
        ) from exc
    if support and published is not None:
        sys.stderr.write(
            "[ticket] Published these knowledge edits with the authored tickets:\n"
            + "".join(f"  {path}\n" for path in support)
        )
