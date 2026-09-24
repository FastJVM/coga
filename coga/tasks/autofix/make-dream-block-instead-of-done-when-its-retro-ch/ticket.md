---
title: Make Dream block instead of done when its Retro checkout can't land
status: draft
owner: nicktoper
agent: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

## What broke

The `recurring/dream` run of 2026-08-31 finished with work it could not land, marked its ticket `done` anyway, and the sweep therefore reported `problems: 0`. Two `coga/log.md` audit-trail lines and a `/tmp` worktree are still stranded on this machine as a result.

From the dream blackboard's `### human-needed` section:

> **Two audit-trail lines are unpushed.** `coga/log.md` lines recording the PR #33 and #34 Slack posts exist only on local branch `dream/retro-2026-W36-1788212557` (worktree `/tmp/dream-retro-2026-W36`). Both `git cherry-pick` and `git push` of that branch were denied by the permission classifier, so Dream could not land them. **The worktree and branch were deliberately preserved rather than removed** — deleting them would destroy the lines.

Verified in the repo as of this sweep:

- `git worktree list` still shows `/tmp/dream-retro-2026-W36  d420b30 [dream/retro-2026-W36-1788212557]`.
- `git log --oneline main..dream/retro-2026-W36-1788212557` → two commits (`d420b30`, `3e4c60a`), both `Sync coga state`.
- `git diff main...dream/retro-2026-W36-1788212557 --stat` → `coga/log.md | 2 ++`. The audit lines are real and are only there.

## Why this is a defect and not just a human-needed note

`coga/recurring/dream/ticket.md:214-221` is explicit about this exact case:

> After the subagent returns, verify every PR branch is pushed, every direct delete is present on the remote control branch, and the isolated checkout is clean. […] **If durability or cleanup cannot be verified, preserve the paths and surface a blocker.**

Dream did the first half (preserved the paths) and skipped the second (surface a blocker). It marked itself `done` and demoted the failure to prose in a blackboard that a later Dream run is designed to retire. Because the ticket status is `done` and the recipe exited 0, the sweep's problem count is 0 and nothing routes anywhere — the failure is invisible to every downstream consumer. Compounding it, `recurring/branch-sweep` will now see `dream/retro-2026-W36-*` forever as `skipped-worktree-pinned` (it already lists six such branches, four in `/tmp`), so the leak is self-perpetuating and silent.

## Where it lives

- `coga/recurring/dream/ticket.md` — the durability/cleanup verification contract at lines ~214-221, and the Phase 6 disposition + final status mark. The template states the blocker requirement but does not make it binding on the terminal status: nothing forbids marking `done` while preserved-unlanded paths exist.
- The Retro-pass delegation section (~lines 188-213) is where the isolated checkout writes `coga/log.md`. Dream's audit lines are append-only history for the *repo*, but they are produced inside a temporary branch whose only exit is a push or cherry-pick the sandbox may refuse — a design that has no fallback.
- `coga/log.md` write path / `coga` sync: whatever appends `Sync coga state` commits in the isolated checkout.

## What a fix has to do

1. **Make the contract binding.** If the isolated checkout is preserved because durability or cleanup could not be verified, Dream must end blocked (`coga block --task recurring/dream --reason ...` naming the branch, worktree path and the unlanded paths), not `done`. Marking `done` with preserved paths should be impossible, not merely discouraged.
2. **Give the sweep something to see.** A recurring task left blocked must count toward the sweep's `problems:` line, so `problems: 0` stops being true when a run stranded work. (Note the related environment gap the same run reported: `[notification.slack].important_webhook` is unconfigured — `coga/coga.toml:75-90` has it commented out — so failure alerts cannot route even once they are raised. Out of scope here, but the alerting path is dead until it is set.)
3. **Remove the single point of failure for audit lines.** Dream's `coga/log.md` history should not depend on a push from a temporary branch succeeding. Either write the repo-global log lines from Dream's own (primary) checkout after the subagent returns, or define an explicit reconciliation the next sync performs for a preserved Dream branch. A denied push is a foreseeable sandbox outcome, not an exceptional one.
4. **Close out the current instance** as part of the fix: land the two commits from `dream/retro-2026-W36-1788212557` onto `main`, then `git worktree remove /tmp/dream-retro-2026-W36 && git branch -D dream/retro-2026-W36-1788212557`. Do not delete either before the two `coga/log.md` lines exist on `main`.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `active`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.
