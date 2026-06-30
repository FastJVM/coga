---
slug: fix-git-recurring-issues
title: Verify recurring high-water git race is fixed and regression-covered
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
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

## Verification note (2026-06-29, nick + claude)

**Verified: high-water merge race is fixed and regression-covered. Closing.**
Note: the relay→coga rebrand (#454, `d0645a19`) renamed all paths; the
ticket's `src/relay/...` references are now `src/coga/...`. Commit `b82440a`
/ PR #357 isn't findable by hash (history rewritten by the rebrand), but the
fix is unambiguously present.

1. **Argument-order fix on `main` ✅ — and structurally robust.**
   `merge_last_serviced_period_text(base, incoming)` (`src/coga/recurring.py:763`)
   resolves the high-water with `max(periods)`. Take-max makes argument order
   *irrelevant*: whichever side holds the more-recent period key wins, so the
   original "args reversed" footgun can no longer drop the newer key. Callsite:
   `_control_blackboard_with_local_period` (`src/coga/commands/recurring.py:660`).

2. **Regression test exists, not skipped, exercises the race ✅.**
   `test_recurring_launch_does_not_resurrect_midflight_handled_period`
   (`tests/test_recurring.py:1781`) pushes a competing commit carrying a handled
   period (`2026-W24`, `remote_cursor: kept`) mid-create, then asserts the stale
   checkout adopts control's more-recent state, the W24 high-water survives, the
   handled period's task is NOT resurrected (`not outcome.ref.path.exists()`),
   and the tree is clean.

3. **No other git footguns surfaced; broad sibling coverage already present:**
   `..._does_not_resurrect_remote_deleted_period_from_stale_main`,
   `..._preserves_midflight_remote_ledger_race`, and a stale-checkout-resume
   test. No state-corruption gap found in the merge/create path.

Tests: `python3.12 -m pytest tests/test_recurring.py` → **82 passed**.

Why no workflow was attached: this ticket was reframed in place from an old bug
stub into a verification gate and never went through the bootstrap interview that
assigns a `workflow:`. Deliverable was a confirming note only (no code to ship),
so closing directly without a workflow per owner decision.
