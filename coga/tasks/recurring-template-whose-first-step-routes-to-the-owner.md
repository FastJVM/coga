---
title: A recurring template whose first step routes to the owner validates clean and fails every firing
status: draft
owner: nicktoper
workflow: null
---

## Description

`coga validate` and `coga recurring list` accept a non-delegating recurring
template whose workflow's first step derives the `owner` role. That includes
a step that simply omits `assignee:`. Every sweep then creates the period,
and `coga launch` refuses it with exit 2, so the job never runs. The ask: report
it as a template error at validate and scan time, before a period is created
with that routing frozen in.

Done looks like: such a template gets a `severity="error"` issue from
`coga validate`, and the recurring scan skips it with that message. It does
not materialize a period that launch will refuse.

## Context

**Seen 2026-09-15 in FastJVM/admin**, on coga `7ccad59f`. Every symbol below
was re-checked on `origin/main` `9203c3b66` (2026-10-08). For two of three due
templates, the sweep printed:

```
Cannot launch recurring/tm-action-reminder: its current step hands off to the owner (zach), not to an agent. ...
recurring/tm-action-reminder failed (exit 2); continuing with the remaining due templates
```

**How admin got there.** #784 made an omitted step role derive `owner`, which
was deliberate per `simplify-ticket-format`. Admin's `surface-due-and-notify`
and `brex-missing-gl` workflows declared no role on their single step, and
relied on a ticket-level `assignee: claude` that #784 also made an error.
Removing that key (FastJVM/admin#225) left 22 templates routing to the owner,
which FastJVM/admin#227 fixed by adding `assignee: agent`. Coga flagged none
of it until launch.

**Why it is worse than a failed launch.** The period is created before the
refusal: its workflow is frozen and its `created … for <period>` ledger line
is written. Fixing the workflow afterwards does not reach that period.
`recurring.create_template` returns the existing live or non-`done` task
instead of re-reading the workflow. The ledger already counts the period as
serviced, so deleting the task skips it. The only way out is a hand
`coga launch <slug> --agent <type>`, and a period left `paused` blocks every
later firing of that template.

**Where.**

- `bump.effective_step_role(steps, 1)` returns `owner` when no step up to
  and including step 1 declares `assignee:`.
- `commands/launch._refuse_human_handoff_launch` refuses any step whose
  operator is human, and bails with exit 2.
- `recurring_runner._launch_due_tasks` catches that `SystemExit` and records
  only `failed (exit 2)`, plus the refusal text as the outcome detail.
- `validate._check_recurring_templates` checks routing only through
  `recurring.delegated_workflow_violation`, and only for templates that
  declare `delegate`. The non-delegating path, both there and in
  `recurring.create_template`, has no routing check.

**Fix.** `recurring._delegated_bound_violation` already rejects an omitted,
`owner`, or peer role, but only for `delegate` templates. That makes it the
obvious model. A sibling check for ordinary templates would take the loaded
`Workflow` and derive step 1's role the same way
(`bump.effective_step_role`). If the role is `owner`, it would report an error
from `validate._check_recurring_templates`, next to the existing
`unbounded-delegated-workflow` issue. It would also make the recurring scan
skip the template rather than materialize it. That catches the mistake where
it is made, in the template, not in a period nobody can repair by editing the
template.

**Open for the owner:**

- Should a template with a reserved `ticket.py` be exempt? Its script runs
  before any agent step.
- Is an owner-first recurring job ever legitimate? If it is, the scan should
  skip it and report it rather than launch it, and validate should warn rather
  than error.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
