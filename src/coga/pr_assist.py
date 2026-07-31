"""Shared authorization for publishing state from a human-step PR assist."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlsplit

from coga import git
from coga.autoclose import (
    GhError,
    parse_branch_name,
    parse_pr_url,
    pr_view,
)
from coga.config import Config
from coga.github_source import redacted_git_source
from coga.repl_supervisor import (
    ASSIST_BRANCH_ENV,
    ASSIST_PR_ENV,
    EXPECTED_TASK_ENV,
)
from coga.taskfile import split_body
from coga.tasks import TaskRef, read_ticket
from coga.ticket import Ticket


@dataclass(frozen=True)
class AssistPublication:
    """A one-transition lease plus its live open-PR publication guard."""

    lease: git.FeaturePublicationLease
    guard: Callable[[str], None]


def _git_remote_repository_identity(
    remote_url: str,
) -> tuple[str, str, str] | None:
    """Normalize a GitHub-style remote URL to ``(host, owner, repository)``."""
    value = remote_url.strip()
    if not value:
        return None

    host = ""
    path = ""
    if "://" in value:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        path = parsed.path
    else:
        left, separator, right = value.partition(":")
        if separator and "/" in right and "/" not in left:
            host = left.rsplit("@", 1)[-1]
            path = right
        else:
            return None

    parts = [part for part in path.strip("/").split("/") if part]
    if not host or len(parts) != 2:
        return None
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository:
        return None
    return host.casefold(), owner.casefold(), repository.casefold()


def verify_recorded_assist_pr_head(
    cfg: Config,
    ticket: Ticket,
    branch: str,
    *,
    expected_pr_url: str | None = None,
) -> str:
    """Return the live open PR head OID after proving its push repository."""
    _, blackboard = split_body(ticket.body)
    pr_url = parse_pr_url(blackboard or "")
    if not pr_url:
        raise git.FeaturePublicationError(
            "recorded assist checkout has no `pr:` link under `## Dev`"
        )
    if expected_pr_url is not None and pr_url != expected_pr_url:
        raise git.FeaturePublicationError(
            f"recorded assist PR changed from {expected_pr_url} to {pr_url}"
        )
    try:
        data = pr_view(
            pr_url,
            "state,url,headRefName,headRefOid,headRepository,headRepositoryOwner",
        )
    except GhError as exc:
        raise git.FeaturePublicationError(
            f"could not verify recorded PR {pr_url}: {exc}"
        ) from exc

    state = str(data.get("state", "")).upper()
    head_branch = str(data.get("headRefName", "")).strip()
    head_oid = str(data.get("headRefOid", "")).strip()
    repository = data.get("headRepository")
    owner = data.get("headRepositoryOwner")
    repository_name = (
        str(repository.get("name", "")).strip()
        if isinstance(repository, dict)
        else ""
    )
    owner_login = (
        str(owner.get("login", "")).strip() if isinstance(owner, dict) else ""
    )
    if state != "OPEN":
        raise git.FeaturePublicationError(
            f"recorded PR {pr_url} is {state or 'missing a state'}, not OPEN"
        )
    if head_branch != branch:
        raise git.FeaturePublicationError(
            f"recorded PR {pr_url} uses head branch {head_branch!r}, not "
            f"recorded branch {branch!r}"
        )
    if not head_oid or not repository_name or not owner_login:
        raise git.FeaturePublicationError(
            f"recorded PR {pr_url} returned incomplete head repository/OID data"
        )

    root = git._toplevel(cfg.repo_root)
    if root is None:
        raise git.FeaturePublicationError(
            "recorded assist checkout is not inside a git repository"
        )
    push_url = git._single_assist_push_url(root, cfg.git_remote)
    pr_host = (urlsplit(pr_url).hostname or "").casefold()
    expected_identity = (
        pr_host,
        owner_login.casefold(),
        repository_name.casefold(),
    )
    remote_identity = _git_remote_repository_identity(push_url)
    safe_push_url = redacted_git_source(push_url)
    if remote_identity is None:
        raise git.FeaturePublicationError(
            f"configured remote {cfg.git_remote!r} push URL "
            f"{safe_push_url!r} does not identify a GitHub repository"
        )
    if remote_identity != expected_identity:
        remote_repo = "/".join(remote_identity[1:])
        pr_repo = f"{owner_login}/{repository_name}"
        raise git.FeaturePublicationError(
            f"configured remote {cfg.git_remote!r} push URL "
            f"{safe_push_url!r} identifies "
            f"{remote_identity[0]}/{remote_repo}, but recorded PR {pr_url} "
            f"publishes from {pr_host}/{pr_repo}"
        )
    return head_oid


def assist_pr_publication_guard(
    cfg: Config,
    ref: TaskRef,
    branch: str,
    *,
    expected_pr_url: str | None = None,
) -> Callable[[str], None]:
    """Re-prove the same open recorded PR immediately before a generated push."""

    def guard(expected_remote_oid: str) -> None:
        try:
            current = read_ticket(ref)
        except Exception as exc:
            raise git.FeaturePublicationError(
                "could not re-read the recorded assist ticket"
            ) from exc
        _, blackboard = split_body(current.body)
        recorded_branch = parse_branch_name(blackboard or "")
        if recorded_branch != branch:
            raise git.FeaturePublicationError(
                f"recorded assist branch changed from {branch!r} to "
                f"{recorded_branch!r}"
            )
        live_pr_oid = verify_recorded_assist_pr_head(
            cfg,
            current,
            branch,
            expected_pr_url=expected_pr_url,
        )
        if live_pr_oid != expected_remote_oid:
            raise git.FeaturePublicationError(
                f"recorded PR head moved from expected {expected_remote_oid} "
                f"to {live_pr_oid}"
            )

    return guard


def assist_publication_from_env(
    cfg: Config,
    ref: TaskRef,
) -> AssistPublication | None:
    """Rebuild a scoped assist capability inherited by an in-session command."""
    branch = os.environ.get(ASSIST_BRANCH_ENV, "").strip()
    expected_task = os.environ.get(EXPECTED_TASK_ENV, "").strip()
    expected_pr_url = os.environ.get(ASSIST_PR_ENV, "").strip()
    if not branch or not expected_task:
        return None
    if Path(expected_task).resolve() != ref.path.resolve():
        return None
    if not expected_pr_url:
        raise git.FeaturePublicationError(
            "inherited assist capability is missing its recorded PR"
        )
    lease = git.feature_publication_lease(cfg, ref.path, branch)
    return AssistPublication(
        lease=lease,
        guard=assist_pr_publication_guard(
            cfg,
            ref,
            branch,
            expected_pr_url=expected_pr_url,
        ),
    )


__all__ = [
    "AssistPublication",
    "assist_pr_publication_guard",
    "assist_publication_from_env",
    "verify_recorded_assist_pr_head",
]
