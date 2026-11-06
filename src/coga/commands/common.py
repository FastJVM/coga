"""Shared helpers for command stubs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import typer

from coga.repl_supervisor import EXPECTED_AGENT_ENV, EXPECTED_TASK_ENV
from coga.task_env import is_script_task

if TYPE_CHECKING:  # pragma: no cover - typing only
    from coga import git
    from coga.config import Config
    from coga.tasks import TaskRef
    from coga.ticket import Ticket


def not_implemented(name: str) -> None:
    typer.secho(f"{name} is not yet implemented.", fg=typer.colors.YELLOW, err=True)
    sys.exit(2)


def current_operator(
    cfg: "Config", ref: "TaskRef", ticket: "Ticket"
) -> str | None:
    """The derived operator's nickname, for routing descriptions and messages.

    A broken snapshot should not stop a human from blocking or commenting on
    a ticket, so an unresolvable operator returns None. Anything that
    *dispatches* resolves the operator directly and refuses loudly instead.
    Completion attribution uses `completion_identity`: the assigned operator
    alone is not evidence of who performed the work.
    """
    from coga.bump import OperatorResolutionError, resolve_operator

    try:
        operator = resolve_operator(
            cfg, ref, ticket, allow_prospective_default=True
        )
    except OperatorResolutionError:
        return None
    return operator.name if operator is not None else None


def completion_identity(
    cfg: "Config",
    ref: "TaskRef",
    ticket: "Ticket",
    *,
    assist_agent: str | None = None,
) -> tuple[str, str]:
    """Audit actor and finisher for bump/mark done, without granting authority.

    Pass an assist agent only after validating its publication capability.
    A script may use that capability, but the deterministic work is still
    credited to system. Task metadata or a configured operator alone says
    nothing about whether an agent actually ran.
    """
    from coga.bump import OperatorResolutionError, resolve_operator

    if is_script_task(ref):
        return "system", "system"
    if assist_agent is not None:
        return f"agent:{assist_agent}", assist_agent
    expected_task = os.environ.get(EXPECTED_TASK_ENV, "").strip()
    if (
        os.environ.get("COGA_SUPERVISED")
        and expected_task
        and Path(expected_task).resolve() == ref.path.resolve()
    ):
        try:
            operator = resolve_operator(
                cfg, ref, ticket, allow_prospective_default=True
            )
        except OperatorResolutionError:
            operator = None
        if operator is not None and operator.is_agent:
            # Credit the agent the supervisor spawned; the routed operator is
            # only who the step was assigned to.
            ran = os.environ.get(EXPECTED_AGENT_ENV, "").strip() or operator.name
            return f"agent:{ran}", ran
    return f"human:{cfg.current_user}", cfg.current_user


def prepare_lifecycle_ticket(cfg: "Config", ref: "TaskRef") -> "git.PreparedTicket":
    """Read `ref`'s ticket from fresh control before a lifecycle transition.

    The one entry every lifecycle command (`bump`, `mark`, `block`,
    `unblock`, `owner`) uses before checking eligibility or deriving
    messages: `git.prepare_ticket` reconciles this checkout's copy with
    control's. An unreconcilable ticket exits 75 so the generic end-of-command
    sweep cannot publish the rejected local state; nothing has been written.
    An ambiguous status conflict first finds or opens its human-review PR
    (`coga.review_conflict`); a human-merged review PR is adopted as the
    resolution. Any other Git failure while preparing is reported and leaves
    today's local read, like an unavailable fetch.
    """
    from coga import git, review_conflict

    path = ref.ticket_path
    try:
        rel, merged = _merged_review(cfg, path)
        if merged is not None:
            return git.prepare_ticket(
                cfg, path, review_base=str(merged["local"]),
                on_resolved=lambda: review_conflict.forget(cfg, rel, merged.get("fingerprint")),
            )
        prepared = git.prepare_ticket(cfg, path)
        if rel is not None and prepared.fresh and prepared.outcome in ("same", "adopted"):
            # The conflict is gone (this checkout took control's copy); a
            # still-open review PR is now the human's to close.
            review_conflict.forget(cfg, rel)
        return prepared
    except git.TicketConflictError as exc:
        review = exc.review
        if review is None:
            _refuse_conflict(ref, exc)
        outcome = review_conflict.escalate(cfg, ref.id_slug, review)
        if outcome.state == "merged":
            # A human already resolved exactly this conflict: adopt it.
            try:
                return git.prepare_ticket(
                    cfg, path, review_base=review.local_oid,
                    on_resolved=lambda: review_conflict.forget(
                        cfg, review.rel, review_conflict.fingerprint(review),
                    ),
                )
            except git.TicketConflictError as again:
                _refuse_conflict(ref, again)
        _refuse_conflict(ref, exc, review_conflict.report(outcome))
    except git.GitError as exc:
        sys.stderr.write(
            f"[git] could not prepare {ref.id_slug} against control ({exc}); "
            "using this checkout's copy\n"
        )
        return git.local_ticket_preparation(path)


def _merged_review(cfg: "Config", path: Path) -> "tuple[str | None, dict | None]":
    """`path`'s repo-relative name when this checkout remembers a review PR
    for it, plus the newest such PR a human merged (else `None`)."""
    from coga import git, review_conflict

    if not cfg.git_enabled or not review_conflict.has_records(cfg):
        return None, None
    try:
        root = git.toplevel(cfg.repo_root)
    except git.GitError:
        return None, None
    if root is None:
        return None, None
    rel = git.relative_to_root(root, path)
    if not review_conflict.recorded(cfg, rel):
        return None, None
    return rel, review_conflict.merged_record(cfg, rel)


def _refuse_conflict(ref: "TaskRef", exc: Exception, review: str | None = None) -> NoReturn:
    from coga import git

    typer.secho(f"Refusing to change {ref.id_slug}: {exc}.", fg=typer.colors.RED, err=True)
    if review is not None:
        typer.secho(review, fg=typer.colors.YELLOW, err=True)
    sys.exit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE)


def bail_ticket_changed(exc: Exception) -> None:
    """Exit 75 after a prepared write found the ticket changed underneath it."""
    from coga import git

    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    sys.exit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE)
