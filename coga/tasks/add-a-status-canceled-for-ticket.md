---
slug: add-a-status-canceled-for-ticket
title: add a status canceled for ticket
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 3 (open-pr)
---

## Description

Add `canceled` as a first-class terminal ticket status in Coga's control
plane. This lets operators close Dream findings and other tickets that were
intentionally declined without misrepresenting them as completed work. Expose
the transition as `coga mark canceled <ticket> --message "<reason>"` and require
a non-empty reason so the decision remains legible in the audit trail.

## Context

`canceled` is terminal: it has no transition back to `active`, and canceling a
ticket clears its current workflow step. The command should accept every
non-terminal ticket state, including `draft`, because unpursued Dream findings
are commonly canceled before activation. Like `done`, canceled tickets are
hidden from the default `coga status` view and included by `--all`; status
totals and help text should represent that behavior clearly.

Treat cancellation as a complete control-plane lifecycle addition rather than
only a validator enum change. Update the shared transition implementation, CLI,
validation and terminal-state invariants, launched-session termination,
read/status views, branch cleanup eligibility, notifications/audit logging,
tests, and user-facing behavioral documentation. Keep the live repo contexts
and packaged template copies synchronized where the contract changes. Do not
add a reopen path or silently reinterpret `canceled` as `done`; completion and
intentional abandonment must remain distinguishable.

Cover cancellation from `blocked` explicitly: existing blocker text remains
historical blackboard content, while the ticket becomes terminal and its
workflow step is cleared. Enforce terminal behavior consistently by rejecting
launch, bump, reactivation, autoclose, and other mutations that require a
non-terminal ticket. Persist the required cancellation reason in the
append-only audit log; it does not need a second canonical copy in the ticket
blackboard or `coga show`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: codex/canceled-ticket-status
worktree: /tmp/coga-canceled-ticket

## Implementation notes
- Plan: add one explicit terminal-status definition shared by lifecycle consumers, expose reason-required cancellation through `mark`, and cover each rejection/visibility/cleanup boundary with focused tests.
- Implemented `canceled` as a distinct terminal outcome across lifecycle validation, launch/queue guards, git state reconciliation, status views, branch cleanup, notifications, and audit logging.
- `coga mark canceled <ticket> --message "<reason>"` accepts draft, active, in-progress, blocked, and paused tickets; it clears `step:` while preserving body/blackboard history.
- Commits after peer-review rebase: `2c6e8002` (`Add canceled ticket lifecycle status`) and `054ee7b7` (`peer-review: apply cancellation lifecycle findings`).
- Freshness: fetched and rebased cleanly onto `origin/main` at `6db7fe86fa04a8e6fe7955f0cfe1dfef0d771185` after the review fixes.
- Final verification: `python -m pytest` (1415 passed, 1 skipped); example fixture `python -m coga.cli validate --json` (2 tasks valid, no issues); `git diff --check`; live/packaged `coga/sync` contexts identical; feature worktree clean and two commits ahead of `origin/main`.
- Peer review (`codex review --base main`) found four must-fix integration gaps: feature-branch cancellation stranded its audit/digest evidence off the control branch; validation failure could leave the ticket canceled before its required audit line was appended; megalaunch counted canceled work as completed; and `recurring --force` let the expected canceled-task refusal escape as an uncaught error and abort later templates.
- Review fix plan: validate cancellation prospectively, add a narrow union-safe control-branch sync for the audit log/digest spool, preserve a distinct megalaunch `canceled` outcome, and turn forced recurring cancellation into a per-template reported error while continuing the sweep.
- Peer-review fixes implemented: cancellation validates an in-memory terminal candidate before touching disk; `mark_canceled` union-lands its audit and installed digest evidence onto control even when the feature branch will never merge; megalaunch reports/counts `canceled` separately; forced recurring scans report canceled-task refusals, continue later templates, and return non-zero.
- Regression coverage includes a real-git feature-branch race where `origin/main` advances concurrently in both union files; the control branch preserves the rival appends plus the cancellation reason/outcome.
- Peer-review verification before freshness rebase: `python -m pytest` (1415 passed, 1 skipped); focused mark/megalaunch/recurring suite (230 passed); `git diff --check` and byte-for-byte live/packaged `coga/sync` context parity clean.

## PR

Add `canceled` as a distinct terminal ticket outcome with a required audit reason, complete lifecycle guards, terminal visibility/counting, cleanup eligibility, notifications, and synchronized behavioral documentation. Peer review also hardened prospective validation, union-safe control-branch delivery of cancellation evidence, distinct megalaunch accounting, and controlled forced-recurring refusals that do not starve later templates.

Test plan: `python -m pytest`; `python -m coga.cli validate --json` from `example/coga`; `git diff --check`.

## Dream Skill: validate-drift

Generated: 2026-07-21T22:54:12+00:00
Command: `coga validate --json --fix`
Task: `add-a-status-canceled-for-ticket`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-21T23:16:56+00:00
Command: `coga validate --json --fix`
Task: `add-a-status-canceled-for-ticket`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-21T23:18:46+00:00
Command: `coga validate --json --fix`
Task: `add-a-status-canceled-for-ticket`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
