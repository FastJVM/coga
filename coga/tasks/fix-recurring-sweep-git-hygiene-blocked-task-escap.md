---
title: 'Fix recurring sweep git hygiene: blocked-task escape, shared branch deletion,
  missing retirement tag'
status: in_progress
owner: nicktoper
agent: claude
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
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

Dream 2026-W35 knowledge-scan findings G11, G12 and G13 -- three defects in
the same unattended recurring-sweep surface.

**G11 -- a blocked period task escapes both safety nets.** A period task that
`coga block`s is auto-paused by `recurring`. The blocker-reminder sweep does
not see it (it is paused, not blocked) and the scheduler does not refire it,
so it goes quiet permanently. See `coga/recurring/blocker-reminders/ticket.md`
and `coga/workflows/blocker-reminders/run.md`. `recurring/resolve-conflicts`
is currently `paused` in exactly this way.

**G12 -- branch-sweep breaks skill-update.** The weekly `branch-sweep` deletes
the shared `coga/skill-update` branch, which the next `skill-update` run then
tries to push to. PR #15 is open on that exact branch right now.

**G13 -- branch-sweep deletes refs without the required tag.** The unattended
`branch-sweep` deletes refs without pushing the `retired/<branch>` tag that
this repo's own retirement policy requires. PR #16 makes that tag mandatory in
`coga/workflows/cleanup/verify-then-retire.md`; `branch-sweep` is the second
path to the same deletion and does not honour it.

## Context

Fix all three in `coga/recurring/{blocker-reminders,branch-sweep,skill-update}/ticket.md`
and the matching `coga/workflows/*` files.

G13 previously carried a launch gate on PR #16. That gate is released: PR #16
merged 2026-08-25, and `coga/workflows/cleanup/verify-then-retire.md` now
requires the `retired/<branch>` tag. G13 makes `branch-sweep` — the second
deletion path — state the same rule.

Current Coga source map (2026-09-28): these templates execute registered
recipes through their `ticket.py` siblings, so prose changes alone cannot
correct their behavior. `src/coga/blocker_reminders.py` plus
`scan_blocker_reminders` owns reminder eligibility; `src/coga/branchsweep.py`
plus `sweep_branches` owns the sweep's protection and deletion gates;
`src/coga/skill_manager.py` plus `SKILL_UPDATE_BRANCH` names the shared updater
branch. The historical cleanup workflow above belongs to the source repo and
does not exist in this checkout. Cite `dev/checkout-cleanup`
(`docs/contexts/dev/checkout-cleanup/SKILL.md`) for the current cleanup proofs,
and `coga/notifications/producers`
(`docs/contexts/coga/notifications/producers/SKILL.md`), “Blocker reminders,”
for reminder delivery and deduplication. Update those owners with the fixes.
<!-- coga:blackboard -->

## Dev

branch: fix-recurring-git-hygiene

## Implementation plan

Owner approved the current-recipe scope in the attended session on 2026-09-28.
Remind once for unresolved asks on paused recurring tasks without changing
their status; direct the owner to launch and answer in the resumed session.
Explicitly protect the shared skill-update branch. Publish a safe
`retired/<branch>` tag before sweep deletion, preserving branches when the
archive cannot be established. Keep the owning topics, skills, templates,
workflows and packaged twins aligned; add behavioral regressions first.

Baseline: `.venv/bin/python -m pytest tests/test_blocker_reminders.py
tests/test_branchsweep.py -q` — 61 passed. Launch checkout started clean on
`main` and fast-forwarded to `origin/main` before branching.

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.
