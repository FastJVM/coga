---
slug: fix-git-recurring-issues
title: Verify recurring high-water git race is fixed and regression-covered
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

**Verification gate for v1 recurring-in-cron.** Started as a bug stub ("fix git
recurring issues"). The most plausible underlying defect — a high-water-mark
merge race where `merge_last_serviced_period_text()` was called with its
arguments reversed (`src/relay/commands/recurring.py:744`) — appears fixed in
PR #357 (`b82440a`), with a regression test
`test_recurring_launch_does_not_resurrect_midflight_handled_period`. Left
unverified, this is a **v1 cron blocker**: a stale checkout's sweep racing the
control branch could lose the more-recent period key, then re-create and
re-launch an already-handled period — duplicate work, duplicate Slack posts,
corrupted `last_serviced_period`.

Confirm, and only close once each is true:

1. The argument-order fix is on `main` and the high-water merge keeps the
   more-recent period key under a concurrent-checkout race.
2. The regression test exists, is not skipped, and actually exercises the race
   (a handled period is not resurrected mid-flight).
3. No other git footguns remain in the recurring path under cron — dirty-tree
   handling, the delete/commit Dream path, and push races don't corrupt state
   or wedge an unattended sweep. If a gap remains, fix it; otherwise the
   deliverable is the confirming note + any missing regression coverage.

## Context

- Reframed from a stale bug stub to a verification gate (owner decision,
  2026-06-16) — fix believed merged in PR #357; this ticket proves it.
- `src/relay/commands/recurring.py` (`_control_blackboard_with_local_period`,
  ~line 744); `src/relay/recurring.py` high-water advance (~lines 335–337);
  `tests/test_recurring.py::test_recurring_launch_does_not_resurrect_midflight_handled_period`.
- Pairs with `wire-recurring-sweep-into-system-cron` and
  `fix-recurring-templates-not-instantiated`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
