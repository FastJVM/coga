---
title: Run clone-local recurring work in every clone
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
contexts:
- coga/recurring
- coga/recurring/scheduling
- coga/recurring/templates
- dev/checkout-cleanup
- dev/checkout-cleanup/branch-sweep
- dev/checkout-cleanup/foreign-ownership
agent: claude
---

## Description

Recurring period tickets are shared through main and serviced once per period by whichever clone sweeps first. That is right for shared state, but wrong for work on clone- or machine-local state. On 2026-10-16 this checkout had 46 local branches (34 with merged PRs) because the daily autoclose always ran from ~/Code/claude/coga; a manual coga run branch-sweep here deleted 28 local + 2 remote, and 9 in ~/Code/codex/coga. Affected jobs: branch-sweep (local refs), the disposal half of autoclose-merged (worktrees/branches; other clones' retires.md entries never discharge), and upstream-coga (reads machine-local [upstream] checkouts). Proposed: a recurring template scope field — repo (default, today's shared period ticket) vs clone (serviced per clone, last-serviced recorded in .coga/, no ticket, no commit) — and split autoclose so ticket closure stays repo-scoped while branch/worktree disposal runs per clone. Tradeoff: clone-scoped runs leave no git-visible record. Alternative considered: an opportunistic local sweep on chat/launch, rejected because a sweep took over 2 minutes of gh lookups. Related: autoclose-re-posts-another-clone-s-primary-checkou, and the cross-clone 'records checkout outside this repository' refusal in branch-sweep reports.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: clone-scoped-recurring

## Plan (agreed with owner 2026-10-16)
- `scope: repo | clone` template field (default repo). Clone scope requires
  `ticket.py`, rejects `delegate:`; no period task, no commit, no log ledger.
- Per-clone ledger + report under the primary checkout's `.coga/recurring/`
  (resolved via git common dir so temp control worktrees record against the
  real clone). Runner sets `COGA_RECURRING_SCOPE=clone`, no `COGA_TASK_SLUG`.
- Runs after shared launches in `run_recurring_scan`; same owner/control/
  inactivity gates; outcomes go to the RunRecord.
- `--all`: duplicate-remote clones get a clone-only child sweep.
- Flip `branch-sweep` (daily) and `upstream-coga` to `scope: clone`; drop
  branch-sweep from `autoclose-merged/ticket.py`.
- Owner decision: per-clone `retires.md` worklist discharge is a follow-up
  ticket (needs its own publish design), not this PR.
