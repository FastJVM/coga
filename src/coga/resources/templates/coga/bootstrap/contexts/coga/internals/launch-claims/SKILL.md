---
name: coga/internals/launch-claims
description: How megalaunch claims a ticket before spawning — exact-byte preflight binding, strict compare-and-set publication of activation and start, the `pending:`/admitted/`released:` launch generation, the held-child proof and admission order, and the local state lock's narrow role.
---

# Megalaunch launch claims

Megalaunch ([megalaunch](../../megalaunch/SKILL.md)) must never let two
checkouts start one ticket revision, never spawn against bytes it did not
preflight, and never leave a ticket claiming a session that did not start.

## Exact-byte preflight

Each launch reads the ticket as raw bytes, parses status, routing, and open
asks from those bytes, and reapplies its gates to them; the queue scan is
only a hint. A picked draft/paused/blocked ticket is captured the same way,
and its prospective `active` view is re-derived from the capture, so a
blocker resolved in the read/capture window leaves an ask-less blocked
ticket that is reported, not started. A task removed during capture fails
that pick without aborting later entries; a reclassification is not a launch
attempt.

`_preflight_agent_launch` then materializes the exact prompt, secret
environment (with supervised witnesses), and agent that spawn will use, and
builds the `in_progress` ticket with a new `launch_generation`:
`pending:<uuid>` with Git sync, a plain UUID without. It refuses an
`in_progress` ticket already carrying any generation form, and checks push
auth. Nothing fallible is re-derived after lifecycle state is written.

## Strict claim publication

Deferred activation (with its source bytes) and the start both use
`strict=True` publication with the source as an exact whole-ticket control
compare-and-set. Before the start write, the local file must still equal the
preflight source bytes. Outcomes:

- `StateRegressionError` or other `GitError` (definitely not on control):
  restore the pre-write bytes and retract this write's audit lines.
- `UncertainPublishError` (push reported failure, control unreadable): keep
  the pending local state as reconciliation evidence and report.
- After `mark_in_progress` returns, the live file must equal the exact
  claimed rendering; a peer change during that sync fails the launch and
  keeps current state.

A refused claim is never compensated backward to `active`.

## The pending seal

Every task publisher refuses to replace a control ticket carrying
`pending:<uuid>` (`git.ticket_regression_reason`); the sole accepted
replacement is the identical ticket with the prefix stripped. A working copy
carrying `released:` is never published. `coga launch` refuses a pending
ticket, and no megalaunch reclaims any generation form (it points at
`coga launch <slug>` for recovery). Step advances and lifecycle transitions
that end or park the session drop the field.

## Held child and admission

`spawn_agent_session` runs with `validate_before_spawn`,
`validate_after_spawn`, a deferred audit, and `after_spawn_release`
([agent spawn](../agent-spawn/SKILL.md)):

1. Before the audit: `_revalidate_launch_claim_before_spawn` requires local
   bytes, then control's copy after a fresh `fetch_control`, then local
   bytes again, all equal to the claim.
2. The PTY child is created but held on a private pipe before exec; the same
   proof runs.
3. Under `git.state_lock`: append the audit, prove again, write the gate
   byte (SIGINT/SIGTERM masked across the write and the released-state
   update), then `_admit_launch_claim_after_release` records a local
   `released:<uuid>` witness and publishes the plain UUID with `expect`
   pinned to the pending copy. The lock is reentrant, so publish re-enters
   it.

Failures: a changed or unverifiable claim before release removes only the
owned audit line, kills the held child, and retains the pending state. A
failed gate write runs compensation first (audit removed, no usage
teardown). An audit failure kills the held child. An admission failure after
release kills the child but keeps its audit and restores the local
`released:` witness, whether publication was refused or uncertain. An
interrupt observed after delivery keeps the audit and treats the child as
launched. So the audit reaches `log.md` only once a child exists, and a
cross-checkout transition after the last fetch is refused while pending or
sees the admitted UUID only after the child can run. Recovery:
[claim recovery](../claim-recovery/SKILL.md).

## The local state lock

`git.state_lock` is a per-checkout advisory `flock` whose file lives in the
system temp directory, outside the worktree. It is reentrant per thread and
released by the kernel on exit, so it leaves no stale state and needs no
cleanup. It serializes this checkout's Coga ticket writers, blocker and
blackboard writers, and `publish`, and it spans megalaunch's append, final
proof, release, and admission. It never decides ownership or launchability.
Cross-checkout safety comes only from the publish compare-and-set.
