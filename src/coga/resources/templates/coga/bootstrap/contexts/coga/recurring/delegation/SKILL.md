---
name: coga/recurring/delegation
description: The `delegate:` contract — a recurring period serviced by one in-process bootstrap agent launch, its frozen dispatch, one-step workflow bound, sentinel completion, and why a template never shells out to a nested `coga launch`.
---

# Recurring delegation

`delegate: bootstrap/<name>` on a template declares *which* stateless bootstrap
target an agent period hands its work to — something no file's presence can
express. It does not choose deterministic versus agent execution; that stays
deduced from `ticket.py`, and the two are mutually exclusive
(`recurring.Template.load`).

## Why delegate instead of a nested launch

A template whose work is "run another Coga command" must declare `delegate:`,
never have its agent shell out to `coga launch`. The recurring supervisor owns
TTY admission only for sessions it spawns; an agent's tool subprocess has no TTY
on stdin or stdout, so a nested agent launch exits 2. Faking a terminal
(`script -qec …`) is not sanctioned. With `delegate:` the sweep itself launches
the target in the operator's terminal — under the sweep's `--agent` override,
queue session conduct and idle/max-session bounds — and keeps the period's
lifecycle bookkeeping, with no wrapper session in between.

## Rules

- **Agent-backed on both ends.** A delegating template is in the agent
  admission class: a headless sweep refuses it before creating the period, and
  skips an already materialized one. The target must itself be agent-backed; a
  bootstrap target with `ticket.py` is rejected before creation — move that
  work into the template's own `ticket.py`.
- **Frozen dispatch.** Creation copies the target into the period ticket. Sweep
  retries, named retries and direct `coga launch recurring/<name>` route only
  from that frozen field, re-read after launch reconciliation, never from the
  mutable template. A period that later acquires `ticket.py` is refused as
  ambiguous. Direct launch activates a paused/draft delegated period inline;
  scheduled and named scans leave paused periods parked.
- **One agent step.** The resolved workflow must have exactly one step that
  explicitly declares `assignee: agent` and no `requires:` gate (even one that
  currently passes). `direct/body` qualifies. Delegation completes the whole
  period on the target's done signal without advancing the workflow, so any
  further step, owner gate, peer role or completion gate would be skipped. The
  bound is checked on the template before materialization and on the frozen
  period before every retry, direct launch and sentinel completion; a refusal
  spawns and completes nothing. `coga validate` reports
  `unbounded-delegated-workflow`. Multi-step, reviewed or gated jobs use
  ordinary recurring execution; role-aware delegation is out of scope.
- **Completion is the target's sentinel.** The period reaches `done` only when
  the bootstrap target emits its done sentinel (for example its `coga slack`
  roll-up line in `coga/log.md`). A natural or crashed exit leaves the period
  retryable. A watchdog timeout in a multi-task sweep is paused and the sweep
  continues only once that pause is verified on control; a named launch leaves
  it `in_progress` for retry.
- **Generation guards.** Start, final spawn, completion and timeout are checked
  against the exact period ticket plus its creator-owned `period_generation`
  on freshly fetched control, and completion also publishes the parent
  template's state with `done`, so an old child can never mutate a later period
  or strand a cursor update locally. Details:
  [recurring-admission](../../internals/recurring-admission/SKILL.md).

Implementation: `recurring_runner._run_delegated_task`,
`recurring.delegated_workflow_violation`, `recurring.frozen_task_delegate`.
