"""Shared helpers for command stubs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

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
    Any other Git failure while preparing is reported and leaves today's
    local read, like an unavailable fetch.
    """
    from coga import git

    try:
        return git.prepare_ticket(cfg, ref.ticket_path)
    except git.TicketConflictError as exc:
        typer.secho(f"Refusing to change {ref.id_slug}: {exc}.", fg=typer.colors.RED, err=True)
        sys.exit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE)
    except git.GitError as exc:
        sys.stderr.write(
            f"[git] could not prepare {ref.id_slug} against control ({exc}); "
            "using this checkout's copy\n"
        )
        return git.local_ticket_preparation(ref.ticket_path)


def bail_ticket_changed(exc: Exception) -> None:
    """Exit 75 after a prepared write found the ticket changed underneath it."""
    from coga import git

    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    sys.exit(git.RETRY_WITHOUT_SWEEP_EXIT_CODE)
