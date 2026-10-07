---
title: Close the presence-not-freshness hole in the branch gate
status: canceled
owner: nicktoper
workflow: null
---

## Description

The `requires: branch` completion gate (`step_gate.STEP_GATES['branch']`) checks that `## Dev` records a usable `branch:`, not that it describes the current attempt. On a retried or relaunched implement, an earlier attempt's branch record can still satisfy that presence check. Reassess whether an additional guard is warranted for ordinary tickets under the current single-checkout workflow, and define the observable failure it would prevent before choosing enforcement. Branch existence alone cannot establish attempt freshness: an earlier attempt's branch may still exist, and resuming it can be legitimate. The scope and done criterion remain to be agreed during authoring.

## Context

Owner clarification (2026-10-06): ordinary ticket work no longer uses linked
worktrees; some recurring jobs still do. Recurring worktrees are outside this
ticket's scope. The original proposal to require a recorded worktree to hold
the branch assumed the retired ordinary-ticket layout and should not be
implemented as written.

`step_gate._has_branch_linkage` checks only the recorded branch text.
`commands.bump.bump` applies completion gates on forward advancement and then
calls `commands.bump._warn_stranded_task_state`, a separate advisory comparison
of committed ticket bytes. The latter does not establish branch ownership by
the current attempt. The earlier ticket
`detect-stranded-ticket-writes-across-checkouts` is provenance for that
distinction, not a dependency on its continued existence.

Current checkout behavior is documented in `dev/checkouts`
(`docs/contexts/dev/checkouts/SKILL.md`), cited rather than attached; read
"Start, work, end" before designing a guard. A supervised session may bump
from its feature branch before launch returns the checkout; a manual session
returns to the control branch first. Therefore a universal requirement that
HEAD equal the recorded feature branch would reject valid manual handoffs.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Obsolescence review — 2026-10-06

Owner suspects this is obsolete and requested a Git check. Local history and
current source support canceling the original proposal:

- `e122d7740` (2026-09-25, PR #896, "stop using worktrees") removed linked
  worktrees from ordinary code-ticket work and changed
  `step_gate._has_branch_linkage` to require only `branch:`. The proposed
  branch/worktree freshness guard targets that retired layout.
- `57f6c04ee` (2026-09-29, PR #909) added the launch checkout boundary.
  The launch boundary's `settle` method publishes routine state before
  `git.prepare_control_checkout` returns the invoking checkout to control;
  unpublished changes prevent that return and stop further chaining.
- `open_pr.open_pr` already rejects a recorded local branch that does not
  exist or has no commits ahead of the base. Adding branch existence at bump
  would move a diagnostic earlier, not establish current-attempt freshness.
- A wrong but existing branch can still pass the presence gate. This is a
  residual possibility, not evidence that the old cross-checkout incident
  still occurs. The proposed probes would not distinguish it from a valid
  resumed branch. No new incident was supplied or established in this review.

Owner approved cancellation as obsolete after this review. Do not add
attempt-tracking machinery; reconsider on a concrete wrong-branch handoff in
the current ordinary-ticket flow.
Recurring worktrees remain out of scope; the documented sandbox clone fallback
does not justify restoring ordinary-worktree assumptions. No implementation or tests were changed. The owner decision is preserved in
`docs/contexts/dev/dev-record/SKILL.md` and its packaged twin.
