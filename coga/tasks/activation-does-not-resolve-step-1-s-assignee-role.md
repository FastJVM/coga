---
slug: activation-does-not-resolve-step-1-s-assignee-role
title: Activation does not resolve step 1's assignee role token
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
