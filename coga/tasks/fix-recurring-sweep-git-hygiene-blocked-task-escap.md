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
step: 2 (peer-review)
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

## Implementation handoff — 2026-09-28

Owner approved the current-recipe scope in the attended session on 2026-09-28.
Commit: `0f25a179a` — Fix recurring sweep git hygiene. Pushed to
`origin/fix-recurring-git-hygiene`; refreshed against `origin/main` with no
rebase needed. Returned the launch checkout to clean, current `main` before
writing this handoff. No PR opened; review and publication remain later steps.

- G11: `blocker_reminders.scan_blocker_reminders` now includes paused recurring
  periods with unresolved asks. A human-paused period with an open ask also
  qualifies, but ordinary paused tasks and terminal/resolved tasks do not.
  Reminder watermarks remain one attempt per blocker and never reactivate the
  task. Paused reminders direct the owner to launch and answer in the resumed
  session, since direct unblock rejects paused status.
- G12: `branchsweep.sweep_branches` explicitly protects
  `skill_manager.SKILL_UPDATE_BRANCH`, independent of ticket and PR state.
- G13: the sweep publishes `retired/<branch>` before any eligible worktree or
  ref deletion. One actual tip must contain all tips being deleted. Conflicting
  tags, divergent tips, or failed publication preserve work and return a
  recorded failure; existing tags are never forced. This applies to the daily
  autoclose branch pass and standalone sweep. Ticket-scoped retire/autoclose
  disposal is outside this archive gate.
- The deletion call now requires the sweep's original archived authorization;
  `branchcleanup.delete_local_branch` also checks the authorized tip on its
  ancestry path. This prevents control advancing or a ref moving during tag
  publication from deleting unarchived work. Branch enumeration uses full refs
  so an archive tag cannot obscure a same-named branch.
- Updated all three recurring templates and workflows, their skills, owning
  topics, and packaged twins. Contracts live in `dev/checkout-cleanup` and
  `coga/notifications/producers`; scheduling and skill-management link to them.

Verification:

- Baseline focused suite: 61 passed. Added regressions first and observed the
  expected failures for all three findings; separately reproduced the
  authorization-race and branch/tag-name cases before fixing them.
- `.venv/bin/python -m pytest tests/test_branchsweep.py tests/test_branchcleanup.py tests/test_blocker_reminders.py -q`
  — 115 passed on the final implementation.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`
  — 3,067 passed in 180.77s on commit `0f25a179a`, including packaging twins.
- From `example/coga`:
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json`
  — 4 OK, no issues.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.cli validate --task fix-recurring-sweep-git-hygiene-blocked-task-escap --json`
  — 1 OK, no issues. `git diff --check` passed.

No unresolved implementation blockers or adjacent findings. Recovery tradeoff:
a conflicting retirement tag or divergent pair of tips requires human
reconciliation rather than overwriting an archive or dropping history.

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.
