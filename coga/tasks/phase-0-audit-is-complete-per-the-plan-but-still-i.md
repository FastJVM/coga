---
title: phase-0-audit is complete per the plan but still in_progress
status: in_progress
owner: nicktoper
agent: claude
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
step: 2 (peer-review)
launch_generation: 3ccc7a10-0d7d-4e31-9a76-3dc8018332d2
---

## Description

`coga/contexts/marketing/plan/SKILL.md` lists `marketing/phase-0-audit` under
"Execution tickets and disposition" as "complete input to this plan; do not
rerun it", and the plan has already absorbed the audit's output — its Phase 0
gate table matches the ticket's `## Proposed phase-1 thresholds` almost line for
line, and the plan's "only publishable narrative evidence is Coga operating on
Coga" absorbs the ticket's `## Plan premise failure`.

The ticket itself is still `status: in_progress` at `step: 2 (human-owns-and-finishes)`.
Its `draft-for-human` step 3 (`report-to-coga`) has therefore never run, and
because it is not `done` it will never be reaped by Dream's done-ticket sweep —
it sits in `coga status` as live work indefinitely. This Dream run's
validate-drift pass also flags it as `stuck-in-progress`, idle for ~139 hours.

The two statements disagree about whether the audit is finished, and one of them
should change.

## Context

Either close the ticket — its substance is now carried by the plan context plus
the nine `cleanup/` tickets it produced — or drop the plan's "complete input"
claim and let the audit finish its own step 3.

Closing is the likelier intent, but it is a lifecycle call on a human-owned
step, so it is the owner's: the ticket is at a `human-owns-and-finishes` step
and an agent should not bump it.

Related: the same task directory carries
`narrative-candidates.md`, which is the subject of the separate ticket
`narrative-candidates-md-publishes-log-text-the-own` — a confidentiality
exposure that should be settled **before** anything closes or archives this task
directory.

<!-- coga:blackboard -->

## Dev

branch: reconcile-audit-lifecycle
worktree: /home/n/Code/claude/coga-reconcile-audit-lifecycle

Separate-checkout layout: linked worktree off `main`; bump runs from the
primary checkout.

## Findings — implement, 2026-09-16

- The contradiction this ticket names is already gone. `6d1ed844` and the
  syncs after it replaced the plan's "complete input to this plan; do not
  rerun it" with "original checks completed … lifecycle remains at the human
  gate until the owner advances it" (`marketing/plan` "Execution tickets and
  disposition"), and the ownership section now says "Its human review step
  remains open; editing these documents does not advance it". The audit
  ticket's own `### Decisions and limits` says it stays at step 2 until an
  explicit owner transition. So the "drop the plan's claim" branch of the
  Context happened outside this ticket.
- Closing the audit is not an agent action: it sits at a
  `human-owns-and-finishes` step, and `narrative-candidates-md-publishes-log-text-the-own`
  (still `draft`) must be settled before its task directory is archived. A
  `coga block` asking the owner to close it now would be asking a question
  the repo already answers ("not yet"), so no block.
- What was left for this ticket was its own exit. `marketing/plan` and
  `marketing/map` both linked this ticket by path as owner of "the audit
  lifecycle question", and `retro/done-ticket` deletes a reaped ticket
  without repairing inbound links. The branch removes both references and
  states where the call lives (the audit's own owner gate, after the
  confidentiality ticket), and rewrites the audit worklist line that named
  this slug. Inbound references to this slug outside `coga/log.md`: 0.
- Marketing contexts have no packaged twin under
  `src/coga/resources/templates/coga/`, so nothing to sync.

## Verification

- `python -m pytest`: 2561 passed (feature worktree).
- `coga validate --json`: issue set identical to the primary checkout
  except the expected `missing-user (config)` from the worktree having no
  `coga.local.toml`; none on the touched files.
- `git diff --check`: clean. Rebased on fresh `origin/main`: already
  up to date, 1 commit ahead, working tree clean.

## For the owner

Nothing in this PR changes a lifecycle. When
`narrative-candidates-md-publishes-log-text-the-own` is resolved, advance
`marketing/phase-0-audit` from step 2 yourself (its step 3
`report-to-coga` then runs, and Dream's done-ticket sweep can reap it).
