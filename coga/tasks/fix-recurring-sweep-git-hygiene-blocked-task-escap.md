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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/914
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

## Peer review

2026-09-28: `codex review --base main` **returned**, exit 0, with three
P2 findings. Its own full-suite run passed 3,067 tests. Findings and disposition:

- Fixed premature retirement tags on dirty or claimed worktrees. The owner
  approved the ordering correction in this session. Claim and local-state
  proofs now precede archival and run again before removal. Regressions cover
  finishing previously dirty work and ignored state appearing during the push.
- Fixed `push.followTags=true` publishing unrelated annotated tags despite the
  explicit refspec. Retirement pushes now pass `--no-follow-tags`.
- The owner explicitly chose **keep the exact-tip requirement** over reusing
  a covering descendant archive after partial cleanup. This review suggestion
  is declined intentionally: if local deletion succeeds but remote deletion
  fails, a later retry can need human reconciliation. The owning
  `dev/checkout-cleanup` topic and packaged twin now state that limitation;
  a regression preserves the decision. Tags are never moved to make it pass.

The new worktree and follow-tags assertions first reproduced three expected
failures. Final verification after `git fetch origin main` and
`git rebase FETCH_HEAD` onto `6ed3a2922`:

- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_branchsweep.py tests/test_branchcleanup.py tests/test_blocker_reminders.py -q`
  — 118 passed in 15.45s.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`
  — 3,070 passed in 192.38s, including packaging twins.
- From `example/coga`:
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json`
  — 4 OK, no issues.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.cli validate --task fix-recurring-sweep-git-hygiene-blocked-task-escap --json`
  — 1 OK, no issues. `git diff --check` and the changed context/twin `cmp` passed.

Manual surface check: ran the actual `coga run blocker-reminders` and
`coga run branch-sweep` CLI paths in a disposable Git repository and bare
remote through a real TTY at 80x24 and 120x40. The driver was
`PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python /tmp/coga-recurring-peer-review-smoke.py`.
Inspected the complete message text through Slack's built-in disabled-delivery
preview, not a live Slack client: paused reminders named launch then unblock;
blocked reminders named unblock; reruns emitted no duplicate reminder and
paused status remained unchanged. Sweep output reported dirty worktrees and
tag conflicts with actionable reasons, preserved the shared updater, and
showed archival before successful deletion. Ref checks confirmed no premature
archive for dirty worktrees and no unrelated release-tag publication with
`push.followTags=true`. Both terminal sizes showed the full linear output.

Published `2b05e9705` — `peer-review: guard retirement publication` — with
`git push --force-with-lease -u origin fix-recurring-git-hygiene`. The branch
has two code commits ahead of `main` (rebased implementation `aab52ee3a` and
the review fix). Returned to clean `main`, fast-forwarded to `24842bd0a`,
before this handoff; changes to main since the rebase were Coga state only.
No unresolved review decisions. No PR opened in this step.

## PR

Paused recurring tasks with unresolved blockers now receive one reminder
without being reactivated, and branch sweep preserves the shared skill-update
branch. Every sweep deletion first publishes the required retirement tag;
worktree eligibility is checked before archival and again before removal,
and the push cannot include unrelated tags through `push.followTags`.
Recurring templates, workflows, owning topics, and packaged twins are aligned.

Exact-tip archive matching remains intentional: partial local/remote cleanup
can require human reconciliation even when an existing archive contains the
remaining tip. Conflicting tags are never overwritten.

Test plan: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest` (3,070 passed); `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.cli validate --task fix-recurring-sweep-git-hygiene-blocked-task-escap --json` (1 OK); from `example/coga`, `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json` (4 OK); `git diff --check`; disposable-repo CLI smoke in 80x24 and 120x40 TTYs.

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.
