"""Step movement — the workflow plane.

`coga bump` normally advances exactly one workflow step; human-triggered
rewinds move to an earlier workflow step. Status transitions
(active/paused/done/canceled) live in `coga.mark`.
"""

from __future__ import annotations

from collections.abc import Callable

import typer

from coga import git
from coga.config import Config
from coga.logfile import append_log, log_path
from coga.notification import post
from coga.tasks import TaskRef
from coga.ticket import Ticket
from coga.validate import assert_task_valid
from coga.workflow import VALID_ASSIGNEE_ROLES


class AssigneeResolutionError(Exception):
    """Raised when a workflow step's role token can't resolve against the ticket."""


REWINDABLE_STATUSES: frozenset[str] = frozenset({"active", "in_progress", "paused"})
"""Statuses a human rewind (`coga bump --to/--backward`) may move the step of.

A rewind is reposition-only: it writes `step:` and never touches `status:`.
`active` and `paused` tickets used to need a launch-then-exit dance purely to
reach `in_progress`; the caller additionally requires their target to resolve
to a configured agent so the unchanged status remains launchable. `draft` has
no step yet, `blocked` belongs to `coga unblock`, and the terminal statuses
have no `step:` at all (`mark_done` pops it).
"""


def rewind_status_error(id_slug: str, status: str) -> str | None:
    """Return why `status` can't be rewound, or None when it can."""
    if status in REWINDABLE_STATUSES:
        return None
    if status == "blocked":
        # `coga unblock` owns blocker resolution; rewinding a blocked ticket
        # would reposition it while leaving the open ask unresolved.
        return (
            f"Task {id_slug} is blocked. "
            f"Run `coga unblock {id_slug}` first, then rewind."
        )
    return (
        f"Task {id_slug} is {status!r}. Cannot rewind. Rewindable statuses: "
        + ", ".join(sorted(REWINDABLE_STATUSES))
        + "."
    )


def resolve_other_agent(cfg: Config, agent: str | None) -> str:
    """Resolve the `other-agent` role token to the peer agent's nickname.

    A declared `[agents.<type>].peer` wins. Without one, "other" means the
    single configured type that is not the ticket's own `agent:`, preserving
    zero-config behavior for two-agent repos. Ambiguity fails loud.
    """
    if not agent:
        raise AssigneeResolutionError(
            "Workflow step declares assignee='other-agent' but the ticket has "
            "no `agent:` field to take the peer of. Add `agent: <type>`."
        )
    # Ticket parsing deliberately preserves malformed frontmatter so validate
    # can report it. Keep role resolution fail-loud for those values instead
    # of letting an unhashable list or mapping escape as a TypeError.
    configured = cfg.agents.get(agent) if isinstance(agent, str) else None
    if configured is not None and configured.peer is not None:
        return configured.peer
    others = [name for name in cfg.agents if name != agent]
    if len(others) != 1:
        if isinstance(agent, str) and agent in cfg.agents and len(cfg.agents) >= 3:
            raise AssigneeResolutionError(
                "assignee='other-agent' needs an unambiguous peer for "
                f"`agent: {agent}`. To fix it, add peer = \"<type>\" to "
                f"[agents.{agent}]. "
                f"Configured agents: {sorted(cfg.agents)}; peer candidates: "
                f"{sorted(others)}."
            )
        raise AssigneeResolutionError(
            "assignee='other-agent' needs exactly two configured `[agents.*]` "
            f"types to pick the peer, with `agent: {agent}` as one of them. "
            f"Configured agents: {sorted(cfg.agents)}; peer candidates: "
            f"{sorted(others)}. Fix coga.toml or the ticket's `agent:`."
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
    rewind: bool = False,
    publish_current_branch: bool = False,
    feature_publication: git.FeaturePublicationLease | None = None,
    feature_publication_guard: Callable[[str], None] | None = None,
    mutation_snapshot: git.FileMutationRollback | None = None,
    after_sync: Callable[[], None] | None = None,
) -> None:
    """Move a ticket to a workflow step.

    If `new_assignee` is given, also rewrites the ticket's `assignee:` to that
    nickname. Caller is responsible for resolving role tokens against the
    ticket beforehand (see `resolve_step_assignee`). Step movement is normally
    silent in Slack; callers set `notify_slack=True` only for an explicit
    operator FYI such as `coga bump --message`. A completion gate may request
    that the transition commit also update the current feature branch; the PR
    gate uses this in primary-checkout development so the PR branch and control
    branch receive the same final ticket state.

    `rewind=True` marks a human `coga bump --to/--backward`, the one deliberate
    backward step move. It relaxes exactly the step-backward rule in the sync
    guard — the human is the authority on their own rewind — while requiring
    the control and working statuses to match exactly. Because rewind never
    changes status, a mismatch proves this checkout is stale. That mismatch is
    propagated before output or notification so the CLI can retain the local
    rewind while suppressing its broader end-of-command state sweep.

    A recorded-assist caller supplies ``feature_publication`` and an armed
    ``mutation_snapshot`` so the step and audit reach the PR and control refs
    under one exact lease before any handoff notification is emitted.
    """
    owner = ticket.owner or cfg.current_user
    # Validate the prospective move before committing it, the way
    # `mark canceled` already does. Not every error this raises is caused by
    # the write: an `other-agent` step that cannot resolve against this
    # machine's `[agents.*]` is a config fact, unchanged by the bump and
    # unfixable by editing the ticket. Validating afterwards would report
    # failure over a ticket already advanced on disk with no audit entry and
    # no sync, and each retry would advance it again.
    prospective = Ticket(frontmatter=dict(ticket.frontmatter), body=ticket.body)
    prospective.frontmatter["step"] = f"{next_step} ({new_step_name})"
    # Advancing the workflow ends the agent session that owned this durable
    # megalaunch claim. The next step may acquire a fresh generation.
    prospective.frontmatter.pop("launch_generation", None)
    if new_assignee is not None:
        prospective.frontmatter["assignee"] = new_assignee
    assert_task_valid(
        cfg,
        ref,
        action=f"bump to step {next_step} ({new_step_name})",
        ticket_override=prospective,
    )
    ticket.frontmatter = prospective.frontmatter
    ticket_bytes = git.write_ticket_under_barrier(
        cfg,
        ticket,
        ref.ticket_path,
        mutation_snapshot=mutation_snapshot,
    )
    audit_append = append_log(cfg, ref.id_slug, actor, log_message)
    if mutation_snapshot is not None:
        mutation_snapshot.arm_append(log_path(cfg), audit_append)

    def sync_state() -> None:
        message = f"Ticket: {ref.id_slug} — step {next_step} ({new_step_name})"
        guard = git.ticket_state_guard(
            cfg, ref.ticket_path, allow_step_rewind=rewind
        )
        if feature_publication is None:
            git.sync_task_state(
                cfg,
                ref.path,
                message=message,
                guard=guard,
                publish_current_branch=publish_current_branch,
                **(
                    {
                        "commit_detached": True,
                        "raise_state_regression": True,
                    }
                    if rewind
                    else {}
                ),
            )
            return
        git.sync_task_state(
            cfg,
            ref.path,
            message=message,
            guard=guard,
            publish_current_branch=publish_current_branch,
            feature_publication=feature_publication,
            feature_publication_guard=feature_publication_guard,
            after_strict_publication=after_sync,
            generated_paths=(
                mutation_snapshot.generated
                if mutation_snapshot is not None
                else None
            ),
        )

    # A recorded-assist child owns a strict feature/control transaction. A
    # rewind also needs its narrower status-equality publication to complete
    # before any user-visible output or notification; if it refuses, the CLI
    # exits through the no-sweep retry path. Ordinary forward bumps keep their
    # established output-before-sync ordering.
    if feature_publication is not None or rewind:
        sync_state()
    if echo is not None:
        typer.echo(echo)
    if notify_slack:
        notification_log = log_path(cfg)
        log_before_notification = (
            notification_log.read_bytes()
            if rewind
            and feature_publication is None
            and notification_log.is_file()
            else None
        )
        # `fatal=False`: the step advance is already on disk above. An
        # undeliverable FYI must not abort `coga bump` before it reaches
        # `emit_done_marker`, or the supervised REPL hangs to its idle timeout.
        post(
            cfg,
            slack_text,
            task_path=ref.path,
            owner=owner,
            watchers=ticket.watchers,
            fatal=False,
            record_failure=feature_publication is None,
        )
        if (
            rewind
            and feature_publication is None
            and notification_log.is_file()
            and notification_log.read_bytes() != log_before_notification
        ):
            # Rewinds deliberately suppress the broad CLI sweep so it cannot
            # bypass their exact-status ticket guard. A failed live post adds
            # one audit line after the scoped rewind publication; publish only
            # that merge=union log, never the ticket again.
            git.sync_paths(
                cfg,
                notification_log,
                [notification_log],
                message=f"Log: {ref.id_slug} — rewind notification failure",
                land_union_files_to_control=True,
                commit_detached=True,
            )
    if feature_publication is None and not rewind:
        sync_state()


__all__ = [
    "advance_step",
    "resolve_step_assignee",
    "resolve_other_agent",
    "rewind_status_error",
    "AssigneeResolutionError",
    "REWINDABLE_STATUSES",
]
