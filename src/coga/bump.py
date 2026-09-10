"""Step movement — the workflow plane.

`coga bump` normally advances exactly one workflow step; human-triggered
rewinds move to an earlier workflow step. Status transitions
(active/paused/done/canceled) live in `coga.mark`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import typer

from coga import git
from coga.config import Config
from coga.lifecycle import TERMINAL_STATUSES
from coga.logfile import append_log, log_path
from coga.notification import post
from coga.tasks import TaskRef
from coga.ticket import Ticket
from coga.workflow import VALID_ASSIGNEE_ROLES


class OperatorResolutionError(Exception):
    """Raised when a ticket's current operator cannot be derived.

    Either the frozen workflow role token does not resolve against this
    machine's `[agents.*]`, or the ticket's live routing inputs (status, frozen
    workflow, current step) are structurally inconsistent. Never swallowed into
    a fallback: guessing an operator is how a human gate gets skipped.
    """


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


@dataclass(frozen=True)
class Operator:
    """Who holds a ticket at one workflow position.

    `role` is the frozen step's routing role — `owner`, `agent`, or
    `other-agent` — and `name` is the concrete nickname it resolved to. Both
    matter: a human gate is identified by its *role*, never by asking whether
    `name` happens to be missing from `[agents.*]`, so renaming a human to
    match an agent type cannot turn a handoff into an automated step.
    """

    role: str
    name: str

    @property
    def is_human(self) -> bool:
        """Whether this operator is a human handoff rather than an agent."""
        return self.role == "owner"

    @property
    def is_agent(self) -> bool:
        return self.role in ("agent", "other-agent")


def resolve_main_agent(
    cfg: Config,
    agent: Any,
    *,
    task_label: str | None = None,
    allow_prospective_default: bool = False,
) -> str:
    """Resolve a ticket's stored main-agent choice to a configured agent type.

    `agent` is the raw `agent:` frontmatter value. An explicitly present value
    must be a non-empty, configured agent name — null, blank, and unknown all
    fail loud rather than silently meaning "the default", because an override
    cannot repair an invalid routing input and a wrong guess here picks the
    wrong reviewer.

    `allow_prospective_default=True` lets an *absent* choice resolve to
    `Config.default_agent()`. Read-only surfaces (status, show, compose,
    validate) and prospective preparation use it to report the agent activation
    *would* select; nothing persists that name except the activation transition
    itself.
    """
    where = f" on {task_label}" if task_label else ""
    if agent is None:
        if not allow_prospective_default:
            raise OperatorResolutionError(
                f"no main agent recorded{where}, but the current workflow step "
                "routes to one. An activated ticket must carry `agent:`; run "
                "`coga mark active` to select the configured default, or choose "
                "one explicitly through authoring."
            )
        default = cfg.default_agent()
        if default is None:
            raise OperatorResolutionError(
                "No agent types are configured; declare at least one "
                "`[agents.*]` table in coga.toml or coga.local.toml "
                "(e.g. `[agents.claude]`)."
            )
        return default.name
    # Ticket parsing deliberately preserves malformed frontmatter so validate
    # can report it. Keep resolution fail-loud for those values instead of
    # letting an unhashable list or mapping escape as a TypeError.
    if not isinstance(agent, str) or not agent.strip():
        raise OperatorResolutionError(
            f"`agent:`{where} must be a non-empty agent name, got {agent!r}."
        )
    name = agent.strip()
    if name not in cfg.agents:
        raise OperatorResolutionError(
            f"`agent: {name}`{where} is not a configured agent type "
            f"(configured: {sorted(cfg.agents)}). Restore that agent's "
            "`[agents.*]` table, or change the ticket's main-agent choice "
            "through authoring — a `--agent` override is ephemeral and cannot "
            "repair an invalid routing input."
        )
    return name


def resolve_other_agent(
    cfg: Config,
    agent: Any,
    *,
    task_label: str | None = None,
    allow_prospective_default: bool = False,
) -> str:
    """Resolve the `other-agent` role token to the peer agent's nickname.

    A declared `[agents.<type>].peer` wins. Without one, "other" means the
    single configured type that is not the ticket's own main agent, preserving
    zero-config behavior for two-agent repos. Ambiguity fails loud.

    Peers are live configuration, not frozen ticket metadata: editing a
    `peer =` changes subsequent peer launches without rewriting any ticket.
    """
    main = resolve_main_agent(
        cfg,
        agent,
        task_label=task_label,
        allow_prospective_default=allow_prospective_default,
    )
    configured = cfg.agents.get(main)
    if configured is not None and configured.peer is not None:
        return configured.peer
    others = [name for name in cfg.agents if name != main]
    if len(others) != 1:
        if len(cfg.agents) >= 3:
            raise OperatorResolutionError(
                "assignee='other-agent' needs an unambiguous peer for "
                f"`agent: {main}`. To fix it, add peer = \"<type>\" to "
                f"[agents.{main}]. "
                f"Configured agents: {sorted(cfg.agents)}; peer candidates: "
                f"{sorted(others)}."
            )
        raise OperatorResolutionError(
            "assignee='other-agent' needs exactly two configured `[agents.*]` "
            f"types to pick the peer, with `agent: {main}` as one of them. "
            f"Configured agents: {sorted(cfg.agents)}; peer candidates: "
            f"{sorted(others)}. Fix coga.toml or the ticket's `agent:`."
        )
    return others[0]


def effective_step_role(steps: Sequence[Any], step_index: int) -> str:
    """The routing role in force at 1-indexed `step_index`.

    A step that omits `assignee:` inherits the nearest *preceding* declared
    role; before any declaration the role is `owner`. This is a scan of the
    frozen steps — not of the audit log, and not a memory of whoever ran the
    task last — so forward moves, restarts, and human rewinds all derive the
    same answer from the same snapshot. A preceding `other-agent` stays that
    role: it is resolved against the ticket's main-agent choice on each read,
    never flattened into a permanent nickname.
    """
    for idx in range(min(step_index, len(steps)), 0, -1):
        entry = steps[idx - 1]
        role = entry.get("assignee") if isinstance(entry, Mapping) else None
        if role:
            return str(role)
    return "owner"


def operator_for_role(
    cfg: Config,
    ticket: Ticket,
    role: str,
    *,
    task_label: str | None = None,
    allow_prospective_default: bool = False,
) -> Operator:
    """Resolve one role token against a ticket's persisted routing inputs."""
    if role not in VALID_ASSIGNEE_ROLES:
        hint = (
            " — `human` was renamed to `owner`; rewrite the frozen snapshot"
            if role == "human"
            else ""
        )
        raise OperatorResolutionError(
            f"Unknown role token {role!r} (expected one of "
            f"{sorted(VALID_ASSIGNEE_ROLES)}){hint}"
        )
    if role == "owner":
        owner = ticket.owner
        if not isinstance(owner, str) or not owner.strip():
            where = f" on {task_label}" if task_label else ""
            raise OperatorResolutionError(
                f"workflow step routes to the owner but no `owner:` is "
                f"recorded{where}."
            )
        return Operator("owner", owner.strip())
    resolver = resolve_main_agent if role == "agent" else resolve_other_agent
    return Operator(
        role,
        resolver(
            cfg,
            ticket.agent,
            task_label=task_label,
            allow_prospective_default=allow_prospective_default,
        ),
    )


def resolve_operator(
    cfg: Config,
    ref: TaskRef | None,
    ticket: Ticket,
    *,
    step_index: int | None = None,
    allow_prospective_default: bool = False,
) -> Operator | None:
    """Derive who holds `ticket` — the one routing rule every consumer shares.

    Pure: it reads config and the ticket's persisted routing inputs (owner,
    main-agent choice, frozen workflow role declarations, current position) and
    returns a value. It never writes, and no command persists what it returns —
    that is the whole point of deriving the operator instead of caching it.

    Returns None only for a terminal task, which has no current operator; the
    read views show a dash. `step_index` derives a *prospective* position (the
    next step before a bump) instead of the ticket's current one.

    Raises `OperatorResolutionError` for a live ticket whose workflow or step is
    missing or inconsistent. That is a structural error by design: falling back
    to the owner would silently convert an agent step into a human handoff, and
    falling back to the agent would skip a human gate.
    """
    label = ref.id_slug if ref is not None else None
    idx = ticket.step_index() if step_index is None else step_index
    if idx is None:
        if ticket.status in TERMINAL_STATUSES:
            # Terminal tasks keep no `step:`, so there is nobody holding them.
            return None
        # A draft — including one whose `workflow:` is still a bare string ref —
        # sits with its owner for triage. `coga launch` derives again from the
        # prepared activation, which freezes the snapshot and seeds step 1.
        return Operator("owner", ticket.owner or cfg.current_user)
    wf = ticket.workflow
    steps = wf.get("steps") if isinstance(wf, dict) else None
    where = f"Task {label}" if label else "Ticket"
    if not isinstance(steps, list) or not steps:
        raise OperatorResolutionError(
            f"{where} is at step {ticket.step!r} but carries no frozen workflow "
            "steps to derive its operator from. Fix the ticket's `workflow:` "
            "snapshot; Coga will not guess a routing role."
        )
    if not 1 <= idx <= len(steps):
        raise OperatorResolutionError(
            f"{where} step index {idx} is outside its frozen workflow "
            f"(1..{len(steps)})."
        )
    return operator_for_role(
        cfg,
        ticket,
        effective_step_role(steps, idx),
        task_label=label,
        allow_prospective_default=allow_prospective_default,
    )


def operator_name(operator: Operator | None) -> str | None:
    """The concrete nickname of an operator, or None for a terminal task."""
    return operator.name if operator is not None else None


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

    Writes `step:` and nothing else about routing: who holds the ticket next is
    derived from the frozen workflow at read time (see `resolve_operator`), so a
    transition has no assignment to write and cannot leave a stale one behind.
    Callers still resolve the prospective operator beforehand — to refuse a move
    whose role cannot resolve, and to name the handoff — but that answer is
    reported, never persisted. Step movement is normally
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
    # Imported lazily: `coga.validate` reaches the routing helpers above through
    # its own deferred imports, and keeping this module free of a top-level
    # dependency on the validator is what lets the pure resolver be imported
    # from anywhere (launch, scripts, views) without a cycle.
    from coga.validate import assert_task_valid

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
    "effective_step_role",
    "operator_for_role",
    "operator_name",
    "resolve_main_agent",
    "resolve_operator",
    "resolve_other_agent",
    "rewind_status_error",
    "Operator",
    "OperatorResolutionError",
    "REWINDABLE_STATUSES",
]
