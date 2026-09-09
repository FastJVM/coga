---
slug: activation-does-not-resolve-step-1-s-assignee-role
title: Activation does not resolve step 1's assignee role token
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (peer-review)
launch_generation: pending:968796b2-283e-4ac5-b989-5ecd9cb87cc9
---

## Description

There are two paths that can land a ticket on step 1 of a frozen workflow, and
they disagree about whether the step's `assignee:` role token is applied.

`create_task` (`coga.create`) resolves it: when `--workflow` is passed it
freezes the snapshot, reads `wf.steps[0].assignee`, and resolves the role
token (`owner` / `human` / `agent` / `other-agent`) against the ticket's
matching role field before writing `assignee:`.

`_freeze_workflow_ref` (`coga.mark`) does not. It converts a bare-string
`workflow:` ref into the frozen dict and seeds `step: 1 (<name>)`, but never
touches `assignee:`. So a hand-authored or guided-authored draft — which
carries `workflow:` as a plain name — activates onto an agent-owned step still
wearing whatever `assignee:` creation defaulted to, normally the human owner.

The result is a ticket that cannot be launched at all. `coga launch`
classifies the target from the ticket's literal `assignee:` field, sees a name
that is not a key in `[agents.*]`, and refuses as a human handoff — on a step
whose own frozen `assignee: agent` says the opposite. `coga bump` is no escape:
it requires `status: in_progress`, which only launch can set. The task is
wedged until a human hand-edits the frontmatter.

Observed on `reuse-the-existing-control-worktree-for-recurring`: hand-authored
draft, auto-activated on launch (`activated (draft -> active) - auto on
launch` in `coga/log.md`), frozen onto `1 (implement)` whose step declares
`assignee: agent`, but left at `assignee: nick`. Both `coga bump` and
`coga launch` refused. Repaired by hand.

Note the asymmetry is invisible until launch time, and the failure names the
wrong cause: the error says "this is a human handoff", which the frozen
workflow contradicts.

Done looks like: activating a draft that carries a bare `workflow:` string and
no `step:` resolves step 1's role token exactly as `create_task` does, so
`coga launch` starts it without a hand-edit; a step-1 role token that cannot
resolve (e.g. `other-agent` with one configured agent) fails loud at
activation with the same message `create_task` gives, rather than deferring a
confusing refusal to launch; a ticket already carrying a step is untouched
(the documented no-op in `coga/architecture` still holds - nothing re-freezes
an existing ticket); and the resolution logic is shared between the two call
sites rather than copied.

## Context

- `coga/architecture` documents `_freeze_workflow_ref` as "a documented no-op
  once `workflow:` is already a dict carrying a step" and describes per-step
  `assignee:` role tokens as resolving "on bump". Whether seeding step 1 at
  activation should also resolve that step's token is the gap this ticket
  closes; update the context in the same PR if the answer changes what is
  written there.
- Existing tickets in the repo that carry `assignee: <human>` on an
  agent-owned step are the same defect and may need a sweep - check before
  deciding whether a migration is in scope.
- Per `ticket-specs-should-cite-symbols-not-line-numbers`, cite symbols.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan

Share one step-1 role resolver between the two paths that land a ticket on
step 1.

- `coga.bump` grows `resolve_first_step_assignee(...)`, layered on a new
  role-mapping primitive that `resolve_step_assignee` also delegates to, so
  `other-agent` handling and the failure text have one home.
- `create_task` (`coga.create`) drops its inline branch and calls it.
- `_freeze_workflow_ref` (`coga.mark`) calls it in the branch that already
  seeds `step: 1`, so only a ticket with no step is touched — the documented
  no-op for an already-stepped ticket holds.
- An unresolvable step-1 token raises `WorkflowError` out of activation.
  Every activation call site (`commands/mark`, `commands/launch` both the
  prospective and the prepare half, `commands/unblock`, `megalaunch`,
  `recurring_runner`) already catches `WorkflowError`, so the loud failure
  lands with the existing "`workflow:` ref could not be frozen" rendering
  and no new plumbing.

Tradeoff: `WorkflowError` reuse over a new exception type means the operator
message is framed as a freeze failure rather than an assignee failure; the
resolver's own text (identical to what `create_task` gives) carries the real
cause, and the alternative is threading a new exception through six call
sites for the same outcome.

## Findings

- Migration sweep (context bullet: "check before deciding whether a migration
  is in scope"). Ten live tickets in this repo carry a human `assignee:` on an
  agent-owned step: `run-recurring-agent-templates-off-the-control-bran`
  (blocked) and nine under `tasks/v2/` (`acceptance-criteria`,
  `automerge-ticket`, `gh-merge-requirement`, `identify-blocking-issues`,
  `implement-accepted-ticket-interview-improvements`, `issue-inbox-slack`,
  `overload-ticket-locally-easily`, `relay-design-repositories`,
  `use-worktree-when-starting-a-dev-task`). All already carry a `step:`, so
  the fix is prospective for them by design. Decided a migration is out of
  scope for this PR: they are repo task state on the control branch, not
  product code, and bundling them into a feature branch collides with the
  routine state syncs that touch the same files. Each is a one-field repair.

## Dev

branch: resolve-step-one-assignee
worktree: /home/n/Code/claude/coga-resolve-step-one-assignee

## Implemented

Commit `28dd114d` on `resolve-step-one-assignee`.

- `coga.bump` — new `resolve_role_token` primitive (role token + explicit role
  mapping + the ticket's own agent). `resolve_step_assignee` is now a
  one-line delegate over the ticket's frontmatter, so bump behavior and its
  messages are unchanged. New `resolve_first_step_assignee` wraps it with the
  `Workflow <name> step 1 assignee=<role>: ...` framing both landing paths
  share.
- `coga.create` — `create_task` drops its inline `other-agent` / role-field
  branch for that call. `other-agent` failure text is byte-identical to
  before; the missing-role-field case now carries the fuller shared message.
- `coga.mark` — `_freeze_workflow_ref` resolves step 1's token inside the
  `if not ticket.step:` branch only, so the already-stepped no-op holds
  including `assignee:`. Resolution happens before either field is written,
  and an `AssigneeResolutionError` becomes `WorkflowError`.
- `WorkflowError` was chosen over a new exception because every activation
  caller (`commands/mark`, `commands/unblock`, `commands/launch` in both the
  prospective-compose and prepare halves, `megalaunch`, `recurring_runner`)
  already catches it, so the loud failure needed no new plumbing and lands
  with the existing "`workflow:` ref could not be frozen" rendering.
- `coga/contexts/coga/architecture` updated in both the live and packaged
  copies: the freeze bullet now names the shared resolver, and the role-token
  bullet says step 1 also resolves at creation/activation and fails there.

## Verification

- `python -m pytest` (via `.venv`): 2322 passed, 1 pre-existing failure.
  - `tests/test_notification_messages.py::test_recurring_create_is_silent`
    fails identically on unmodified `main` (`IsADirectoryError` on
    `coga/tasks/work`) — unrelated to this change, not fixed here.
  - `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`
    deselected: it shells out to `pip`, which this `.venv` does not have.
    The twin byte-identity test it sits next to did run and passes.
- Three tests added to `tests/test_mark.py`, mirroring
  `test_mark_active_freezes_string_workflow`: role token resolved on
  activation, unresolvable token refused with the ticket untouched, and an
  already-stepped ticket left alone. The first two fail on the unmodified
  `mark.py`; the third passes both ways as a no-op guard.
- `coga validate --json` against `example/coga`: 3 ok, no issues.
