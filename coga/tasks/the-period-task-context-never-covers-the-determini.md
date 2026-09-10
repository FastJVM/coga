---
title: The period-task context never covers the deterministic ticket.py firing
status: draft
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
step: 1 (implement)
---

## Description

`src/coga/recurring.py` auto-attaches `coga/period-task` to **every** period
task unconditionally — the create path even strips a hand-added duplicate. But
five of the seven shipped templates (`autoclose-merged`, `blocker-reminders`,
`branch-sweep`, `digest`, `skill-update`) carry the reserved `ticket.py`
sibling, and `coga/contexts/coga/recurring/SKILL.md` states plainly that for
those "no agent starts"; their skills each repeat "no agent, no composed
prompt".

The context is written end to end for an agent — "You are a period task", "read
the blackboard region … to find where the previous run stopped", "finish the
current workflow step with `coga bump` — or `coga mark done` when your
workflow's only step is `direct/body`" — and nowhere says that for a `ticket.py`
template the recipe performs that bookkeeping in code and no reader of this
context exists.

The corpus shows the consequence: a committed sweep run-log records three
completed deterministic runs whose period blackboards contain nothing but the
untouched seeded placeholder.

## Context

Add a short section to `coga/contexts/coga/period-task/SKILL.md` and its
enforced packaged twin under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/`
distinguishing the agent-backed firing from the deterministic `ticket.py`
firing, so the parent-blackboard state contract reads as "whoever runs this
period, agent or recipe" rather than as instructions to an agent that is never
spawned.

Two neighbouring items land in the same area and are already routed this Dream
run — a proposal PR correcting the recurring context's `ticket.py` dispatch
description (it is not binary; a hybrid script chains into an agent phase), and
the sibling ticket `define-the-recipe-reporting-contract-report-durabi`. Read
both before writing so the three agree on one story.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
