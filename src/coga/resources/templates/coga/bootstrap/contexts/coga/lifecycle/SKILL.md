---
name: coga/lifecycle
description: The two per-ticket state machines — status (whether work happens) and step (where in the frozen workflow) — with the single writer for each transition, blocking and blocked resume, bump and human rewind, cancellation rules, and the read-only `coga status` triage views.
---

# Ticket lifecycle

Each ticket has two independent state machines, and each state change has
one shared writer. Workflow shape and routing are
[coga/workflows](../workflows/SKILL.md).

## Status: whether work happens

Values: `draft`, `active`, `in_progress`, `paused`, `blocked`, and the
terminal outcomes `done` and `canceled`.

| Transition | Writer | Allowed from |
| --- | --- | --- |
| create `draft` | `coga create` (ignores `default_status`) | — |
| `active` | `coga mark active` | `draft`, `paused` |
| `in_progress` | `coga launch`, as script or agent work begins | `active` |
| `paused` | `coga mark paused` (keeps `step:`) | `active`, `in_progress` |
| `done` | `coga mark done`, or final-step `coga bump` (clears `step:`) | `active`, `in_progress` |
| `canceled` | `coga mark canceled --message <reason>` (clears `step:`) | any non-terminal |
| `blocked` | `coga block --task <ref> --reason ...` (keeps `step:`) | `active`, `in_progress`, `blocked` |
| `blocked → active` | `coga unblock` (keeps `step:`; on `in_progress` or a paused `recurring/` period it only resolves asks) | `blocked` |

Every writer above except launch decides from the ticket reconciled with
freshly fetched control, not this checkout's possibly stale copy: a terminal
control copy cannot be reopened by a stale `mark active`, pause, or block, and
owner and `requires:` gates are rechecked there
([prepared ticket transactions](../state-publication/SKILL.md#prepared-ticket-transactions)).

Launching is itself the
readiness signal: `coga launch` performs `mark active` inline on a `draft` or
`paused` ticket before flipping it to `in_progress`. Activation refuses a
ticket with no workflow, empty required extension fields, or unsynthesized
pre-launch authoring notes on the blackboard
([coga/blackboard](../blackboard/SKILL.md)); first activation also fills
`agent:` and freezes a bare workflow ref ([coga/tickets](../tickets/SKILL.md)).
Tickets without a workflow move through statuses only via `coga mark`.

For an ordinary managed agent launch, activation and start are prepared in
memory and published as the final `in_progress` ticket with checkout linkage
and the launch audit. Their distinct audit events remain ordered; there is
no separately published intermediate `active` state. Standalone commands and
strict queue/recurring callers keep their own immediate transitions.
[Launch publication boundaries](../state-publication/launch-boundaries/SKILL.md)
owns the accounting; [checkout preparation](../checkouts/launch-boundary/SKILL.md)
owns refusal and retained-state recovery.

- `--message` adds an FYI to active/paused/done notifications; for canceled
  it is the required audit reason, appended to `coga/log.md`. Cancellation
  leaves the body and blackboard (including open blocker text) untouched.
- Completion writes the local ticket and audit log. Follow [Git](../git/SKILL.md)
  to carry branch state through a PR.
- Mark abandoned or superseded work `canceled` with the reason. A final bump
  for a PR-backed ticket records `done` on the branch so the merge carries
  that status to the base. See [coga/git](../git/SKILL.md).
- A terminal transition is a verdict about the ticket, never a repair of
  validator output. "Clears a validate error" is not a cancellation reason:
  cancelling parked drafts is the cheapest route to a green gate and trades
  the record of intent for an exit code.
- A cancellation that records an owner decision *not* to act is a verdict
  worth keeping, and the ticket is not where it lives: land it in the topic
  [coga/knowledge](../knowledge/SKILL.md) names, before or with the cancel,
  and let the cancellation reason point there. Dream's knowledge scan is the
  backstop for one that did not land.

## Blocking and resume

`coga block --task <id> --reason "<ask>"` records an ask and sets the ticket
to `blocked`. On an attended agent launch the preamble shows the open asks.
Launch leaves the ticket blocked, including when the session exits without
an answer. A blocked script requires an answer before launch.

`coga unblock <id> --answer "<answer>"` records the answer and returns a
blocked ticket to `active`. In a launched session for that ticket, it moves
to `in_progress`. A paused recurring period's existing pause is preserved
when its asks are resolved.

## Step: where in the workflow

`step:` is `N (step-name)`, owned entirely by `coga bump`.

- Bare `coga bump <ref>` requires `in_progress`, or `active` when a human
  runs it outside a supervised launch on an owner-held step (launch refuses
  that step, so it could not otherwise reach `in_progress`), checks the leaving step's
  `requires:` gate, and advances one step, or on the final step delegates to
  `mark_done`. A supervised bump whose session was composed for a step
  other than the one reconciled with control refuses as stale context. A
  workflow-less ticket is refused with a pointer to `coga mark done`. `--message` rides the transition notification. A forward
  bump from a step with a usable `## Dev` `branch:` warns on stderr (never
  blocks) about stranded ticket writes; see
  [Git](../git/SKILL.md).
- `--to` / `--backward` is a **human** rewind; agents inside a supervised
  launch are refused (`COGA_SUPERVISED`). It is recovery when a step went
  wrong but the ticket's premise still holds: because status and blackboard
  are untouched, everything learned stays. When the premise itself turns out
  wrong, the usual move is not a rewind:
  cancel the ticket with its reason, update the context that owns the fact,
  and open a new ticket. It repositions only: accepts
  `active`, `in_progress`, `paused`, never changes
  status, and derives the target operator without persisting it. From
  `active`/`paused` it must target an agent step (an owner step could not be
  resumed or bumped); `in_progress` may target either. It refuses `blocked`
  (unblock first) and terminal tickets. It moves backward from the step
  reconciled with control. If its guarded publication is not confirmed, the local mutation is left for inspection: reconcile the checkout
  with control before another mutating command, push, or merge.

Pausing preserves the step; cancellation clears it.

## Triage: `coga status`

The editable report lives in [bootstrap/status](../../../status/ticket.md),
reached through a read-only alias. A pure read: no mutation, no network. It lists live tasks; `--all` adds
terminal ones with separate counts. `coga status <dir>` limits to a subtree,
`--no-recurse` to one level, `--dirs` lists plain directories instead; an
unknown directory fails listing those that exist. `updated` comes from the
task's last `coga/log.md` line, falling back to the last commit touching its
files (or `-` without git). `--blocked` shows one row per open ask on
`status: blocked` tasks. When the view covers `tasks/recurring/`, a one-line
`Recurring` footer summarizes templates, due counts and load errors (full view:
`coga recurring list`, [coga/recurring](../recurring/SKILL.md)).

## Dependencies and supersession

A dependency is an open blocker ask on the **dependent** ticket:
`coga block --task <B> --reason "Depends on <A>: <what B needs from it>"`.
Use A's exact path-qualified slug (for example `v2/some-ticket`), as a whole
token, not its title or a partial slug. B must be active, in_progress, or
blocked; activate a draft first. This uses the existing blocker mechanism:
status and reminders show the ask, and the
[megalaunch dependency drain](../megalaunch/SKILL.md#dependency-drain) resolves
each dependency ask only when its exact named task is `done` or was seen
earlier in that run and has since been retired. With multiple dependencies,
satisfied asks resolve individually; unfinished dependencies and unrelated
human asks stay open, and B stays `blocked` while any ask remains. If an ask
names multiple known task refs, all must be finished before that ask resolves.
An explicit human `coga unblock` answer still resolves all open asks in one
transition. This is not a general dependency graph or a `dependencies:` field,
and cancellation does not count as completion.

When a newer ticket supersedes an older one, use
`coga mark canceled <old> --message "Superseded by <new>"`, with the successor's
exact path-qualified slug. The cancellation reason starts with `Superseded by `;
an optional date or explanation may follow. Cancellation removes the old ticket
from live queues, clears its step, and keeps its body and blackboard as history.
There is no separate `superseded` status. Leaving the replaced ticket paused or
draft keeps it live. If file readers need the pointer, open `## Context` with
**Superseded by `<new>` (<date>).** as a courtesy copy of the logged reason.
A superseded design within one ticket follows
[coga/blackboard](../blackboard/SKILL.md#superseded-designs).
