---
name: human/run
description: The owner performs the task, records its evidence, and confirms completion without agent steps.
steps:
  - name: execute
    assignee: owner
---

## execute

When ready to begin a draft, the owner runs `coga mark active <slug>`.
No agent launch is needed for this owner-held step.

The owner performs the work described in the ticket and records the result,
evidence, and any remaining failures on its blackboard. Keep the ticket open
until its done criteria are met. When they are, the owner runs
`coga mark done <slug>` to close this single-step ticket. An agent assist,
if explicitly requested, does not take over execution or close the ticket
without the owner's explicit instruction.

Use `mark done` for this human-only path: `mark active` leaves the ticket
`active`, whereas `bump` requires an `in_progress` ticket from a launch.

## No other-agent code review

This workflow records human execution and evidence. Product code changes
belong on separate `code/*` tickets with their own review steps.
