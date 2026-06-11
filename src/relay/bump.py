"""Step movement — the workflow plane.

`relay bump` normally advances exactly one workflow step; human-triggered
rewinds move to an earlier workflow step. Status transitions
(active/paused/done) live in `relay.mark`.
"""

from __future__ import annotations

import typer

from relay import git
from relay.config import Config
from relay.logfile import append_log
from relay.slack import post
from relay.tasks import TaskRef
from relay.ticket import Ticket
from relay.validate import assert_task_valid
from relay.workflow import VALID_ASSIGNEE_ROLES


class AssigneeResolutionError(Exception):
    """Raised when a workflow step's role token can't resolve against the ticket."""


def resolve_other_agent(cfg: Config, agent: str | None) -> str:
    """Resolve the `other-agent` role token to the peer agent's nickname.

    "Other" means the configured `[agents.*]` type that is not the ticket's
    own `agent:` — the peer reviewer. This is only unambiguous when exactly
    one such candidate exists (i.e. two agent types are configured and the
    ticket's `agent:` is one of them). Anything else (no `agent:`, the
    `agent:` isn't a configured type, only one type, or three+) is a
    fail-loud condition rather than a silent guess.
    """
    if not agent:
        raise AssigneeResolutionError(
            "Workflow step declares assignee='other-agent' but the ticket has "
            "no `agent:` field to take the peer of. Add `agent: <type>`."
        )
    others = [name for name in cfg.agents if name != agent]
    if len(others) != 1:
        raise AssigneeResolutionError(
            "assignee='other-agent' needs exactly two configured `[agents.*]` "
            f"types to pick the peer, with `agent: {agent}` as one of them. "
            f"Configured agents: {sorted(cfg.agents)}; peer candidates: "
            f"{sorted(others)}. Fix relay.toml or the ticket's `agent:`."
        )
    return others[0]


def resolve_step_assignee(cfg: Config, ticket: Ticket, role: str) -> str:
    """Resolve a workflow step's role token to a concrete nickname.

    `role` must be one of `owner` | `human` | `agent` | `other-agent`.
    The first three read the matching ticket field; `other-agent` derives
    the peer agent from config. Raises AssigneeResolutionError when the
    token can't resolve.
    """
    if role not in VALID_ASSIGNEE_ROLES:
        raise AssigneeResolutionError(
            f"Unknown role token {role!r} (expected one of {sorted(VALID_ASSIGNEE_ROLES)})"
        )
    if role == "other-agent":
        return resolve_other_agent(cfg, ticket.agent)
    value = ticket.frontmatter.get(role)
    if not value:
        raise AssigneeResolutionError(
            f"Workflow step declares assignee={role!r} but ticket has no `{role}:` field. "
            f"Add `{role}: <nickname>` to ticket frontmatter."
        )
    return str(value)


def advance_step(
    cfg: Config,
    ref: TaskRef,
    ticket: Ticket,
    *,
    next_step: int,
    new_step_name: str,
    actor: str,
    log_message: str,
    slack_text: str,
    digest_detail: str,
    new_assignee: str | None = None,
    notify_slack: bool = False,
    echo: str | None = None,
) -> None:
    """Move a ticket to a workflow step.

    If `new_assignee` is given, also rewrites the ticket's `assignee:` to that
    nickname. Caller is responsible for resolving role tokens against the
    ticket beforehand (see `resolve_step_assignee`). Step movement is normally
    silent in Slack; callers set `notify_slack=True` only for an explicit
    operator FYI such as `relay bump --message`.
    """
    owner = ticket.owner or cfg.current_user
    ticket.frontmatter["step"] = f"{next_step} ({new_step_name})"
    if new_assignee is not None:
        ticket.frontmatter["assignee"] = new_assignee
    ticket.write(ref.path / "ticket.md")
    assert_task_valid(cfg, ref, action=f"bump to step {next_step} ({new_step_name})")
    append_log(ref.path, actor, log_message)
    if echo is not None:
        typer.echo(echo)
    if notify_slack:
        post(cfg, slack_text, task_path=ref.path, owner=owner, watchers=ticket.watchers)
    git.sync_task_state(
        cfg,
        ref.path,
        message=f"Ticket: {ref.id_slug} — step {next_step} ({new_step_name})",
    )


__all__ = [
    "advance_step",
    "resolve_step_assignee",
    "resolve_other_agent",
    "AssigneeResolutionError",
]
