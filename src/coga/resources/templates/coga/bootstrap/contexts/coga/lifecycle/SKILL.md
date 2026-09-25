---
name: coga/lifecycle
description: The two per-ticket state machines — status (whether work happens) and step (where in the frozen workflow) — with the single writer for each transition, blocking and blocked resume, bump and human rewind, cancellation rules, writer validation timing, and the read-only `coga status` triage views.
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
| `blocked → active` | `coga unblock` (keeps `step:`) | `blocked` |

The shared finalizers live in `src/coga/mark.py`. Launching is itself the
readiness signal: `coga launch` performs `mark active` inline on a `draft` or
`paused` ticket before flipping it to `in_progress`. Activation refuses a
ticket with no workflow, empty required extension fields, or unsynthesized
pre-launch authoring notes on the blackboard
([coga/blackboard](../blackboard/SKILL.md)); first activation also fills
`agent:` and freezes a bare workflow ref ([coga/tickets](../tickets/SKILL.md)).
Tickets without a workflow move through statuses only via `coga mark`.

- `--message` adds an FYI to active/paused/done notifications; for canceled
  it is the required audit reason, appended to `coga/log.md`. Cancellation
  leaves the body and blackboard (including open blocker text) untouched.
- `done` and `canceled` are terminal: launch refuses them and nothing
  reactivates a canceled ticket. `mark done --force` / final-step
  `bump --force` finish a `direct/body` ticket while acknowledging product code
  stranded off the control branch.
- `done` is a control-plane transition, not a receipt: a done ticket's own
  verification prose is no proof that the change its `## Description` scoped
  reached the control branch. `retro/done-ticket` checks the scope against the
  tip before extracting it.
- A terminal transition is a verdict about the ticket, never a repair of
  validator output. "Clears a validate error" is not a cancellation reason:
  cancelling parked drafts is the cheapest route to a green gate and trades
  the record of intent for an exit code.

## Blocking and resume

`coga block` appends the ask under `## Blockers`, sets `blocked`, logs and
syncs, notifies the owner live, and ends a launched session. The reason
should be answerable from `coga status --blocked` alone.

`coga unblock <ref> --answer "..."` marks each open ask `- [x]` with a
`resolved:` line and returns the task to `active` at the same step; without
`--answer` it prompts after showing the asks. On an `in_progress` ticket with
open asks it only resolves them. `coga unblock --all` walks every blocked task,
prompting per task (blank skips; `--answer` is rejected) and ends with an
`Unblocked N, skipped M` summary.

An **interactive** (TTY) launch resumes a blocked ticket inline
(`blocked → active → in_progress`, step preserved) and composes the
resolve-or-re-block preamble ([coga/prompt-composition](../prompt-composition/SKILL.md)).
If any resumed phase, including a `ticket.py` that fails, pauses, closes or
advances, exits before an answer is recorded, launch returns the ticket to
`blocked`, restoring the original step and routing inputs if a terminal
transition cleared them; an invalid baseline fails closed. TTY-less launches
refuse a blocked ticket until `coga unblock` records an answer.

## Step: where in the workflow

`step:` is `N (step-name)`, owned entirely by `coga bump` (`src/coga/bump.py`).

- Bare `coga bump <ref>` requires `in_progress`, checks the leaving step's
  `requires:` gate, and advances one step, or on the final step delegates to
  `mark_done`. A workflow-less ticket is refused with a pointer to
  `coga mark done`. `--message` rides the transition notification. A forward
  bump from a step with a usable `## Dev` `branch:` warns on stderr (never
  blocks) about stranded ticket writes; see
  [dev/checkouts](../../dev/checkouts/SKILL.md).
- `--to` / `--backward` is a **human** rewind; agents inside a supervised
  launch are refused (`COGA_SUPERVISED`). It repositions only: accepts
  `active`, `in_progress`, `paused` (`REWINDABLE_STATUSES`), never changes
  status, and derives the target operator without persisting it. From
  `active`/`paused` it must target an agent step (an owner step could not be
  resumed or bumped); `in_progress` may target either. It refuses `blocked`
  (unblock first) and terminal tickets. If its guarded publication is not
  confirmed, the local mutation is left for inspection: reconcile the checkout
  with control before another mutating command, push, or merge.

Pausing preserves the step; cancellation clears it.

## Writer validation timing

`src/coga/validate.py` `assert_task_valid` leaves a bad written ticket on disk
for the operator to fix, which is safe only for checks keyed off ticket
content. A check that can fail on configuration (such as
`unresolvable-step-assignee`) must run against a **prospective** copy before
writing: copy the `Ticket`, apply the change, pass
`ticket_override=...`, then write, log and sync. `mark_done`,
`mark_canceled`, bump's step advance the assist freeze, and `coga owner` do this;
`mark_active`, `mark_in_progress`, `mark_blocked`, and `mark_paused` still
validate after writing.

## Triage: `coga status`

A pure read: no mutation, no network. It lists live tasks; `--all` adds
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
[megalaunch dependency drain](../megalaunch/SKILL.md) can retry B once A is
`done` or retired. It is not a general dependency graph or a `dependencies:`
field, and cancellation does not count as completion.

When a newer ticket supersedes an older one, use
`coga mark canceled <old> --message "Superseded by <new>"`, with the successor's
exact path-qualified slug. The cancellation reason starts with `Superseded by `;
an optional date or explanation may follow. Cancellation removes the old ticket
from live queues, clears its step, and keeps its body and blackboard as history.
There is no separate `superseded` status. Leaving the replaced ticket paused or
draft keeps it live. If file readers need the pointer, open `## Context` with
**Superseded by `<new>` (<date>).** as a courtesy copy of the logged reason.
A superseded design within one ticket follows [dev/code](../../dev/code/SKILL.md).
