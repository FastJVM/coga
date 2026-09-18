---
name: maintenance/with-approval
description: Inventory a maintenance task, obtain owner approval of concrete changes, then clean up and verify.
steps:
  - name: inventory
    assignee: agent
  - name: approve
    assignee: owner
  - name: cleanup-and-verify
    assignee: agent
---

## inventory

Read the ticket's Description and Context as the maintenance specification.
Inspect the relevant state without performing cleanup. Record the inventory,
an exact proposed action list, reasons, preservation decisions, and verification
plan on the blackboard. Make the list concrete enough for the owner to approve
individual actions. When it is ready for review, run `coga bump <slug>` and stop.

## approve

Review the inventory and proposed actions with the owner. Record exactly which
actions and targets they approve, which must be retained, and any conditions.
Resolve requested changes to the list without performing cleanup. Advance with
`coga bump <slug>` only when the owner explicitly approves the concrete list
and asks to proceed; authoring or launching the ticket is not that approval.

## cleanup-and-verify

Read the approved actions and the ticket's preservation rules. Recheck the
relevant state immediately before each action; preserve and report targets
whose state changed or whose eligibility is uncertain. Execute only approved,
still-eligible actions. Verify the result and record completed actions,
remaining items, failures, and any measurements required by the ticket.
Resolve failures or obtain the owner's acceptance of explicitly recorded
partial completion before finishing. When the agreed work is complete, run
`coga bump <slug>` and stop.
