"""Shared helpers for command stubs."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import typer

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
    """The derived operator's nickname, for CLI attribution and messages.

    Commands that record who acted (`bump`, `block`, `slack`, `mark`) need a
    name, not a routing decision, and must not fail over one: a broken snapshot
    should not stop a human from blocking or commenting on a ticket. So an
    unresolvable operator returns None and the caller falls back to
    `cfg.current_user`. Anything that *dispatches* resolves the operator
    directly and refuses loudly instead.
    """
    from coga.bump import OperatorResolutionError, resolve_operator

    try:
        operator = resolve_operator(
            cfg, ref, ticket, allow_prospective_default=True
        )
    except OperatorResolutionError:
        return None
    return operator.name if operator is not None else None
