---
name: coga/tickets/ownership
description: Reassigning a ticket's human of record with `coga owner`, its gates and package-private transaction, and how ticket-to-ticket relationships are expressed.
---

# Ownership and ticket relationships

Part of [coga/tickets](../SKILL.md).

`owner:` is the human of record: owner steps route to that person, megalaunch
filters by owner, and notifications mention them. Reassign with
`coga owner <slug> <name>`. There is no independent `assignee:` or legacy
`human:` field to update. The command preserves status, step, and body, rejects
blank or unchanged names and terminal records, and writes an audit line without
a Slack post.

An `in_progress` agent step must stop and be paused before reassignment. An
`in_progress` **owner-held gate** instead requires `--assist-stopped`: the
human confirms any assisting agent has stopped, from outside that ticket's
supervised session. This preserves the gate so its new owner can still bump
it. Coga has no cross-checkout live-session registry; the flag is an explicit
human attestation, not an automatic liveness check. A supervised session cannot
reassign its own ticket, and an outstanding `launch_generation` is refused;
stop the session and follow [claim recovery](../../internals/claim-recovery/SKILL.md)
first. Reassignment never clears or invalidates a launch claim.

The package-private transaction is why this command lives in core: it holds
`git.state_lock` across the read, prospective validation, local byte comparison,
write, audit, and strict publication with the original ticket bytes as `expect`.
A concurrent local edit is preserved. A definite publication failure restores
only the command's own ticket bytes and retracts its audit; an uncertain push
keeps the write for reconciliation. Both failures exit 75 to suppress the generic
sweep. Refresh/reconcile control before retrying. With Git disabled or unavailable
through a documented soft-skip, the local write remains the result
([state publication](../../internals/state-publication/publish/SKILL.md)).

Ticket-to-ticket relationships use the dependency and supersession conventions
in [coga/lifecycle](../../lifecycle/SKILL.md), rather than new `dependencies:` or
`superseded_by:` frontmatter. Successor-side “this blocks X” prose is a human
pointer, not machine-readable ordering.
