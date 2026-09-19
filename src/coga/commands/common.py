"""Shared helpers for command stubs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from coga.repl_supervisor import EXPECTED_TASK_ENV
from coga.task_env import is_script_task

if TYPE_CHECKING:  # pragma: no cover - typing only
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
            return f"agent:{operator.name}", operator.name
    return f"human:{cfg.current_user}", cfg.current_user
