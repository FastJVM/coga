---
slug: recurring/rebase-stale-worktrees
title: Rebase stale worktrees
status: paused
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
script: null
step: 1 (execute)
---

## Description

Bring live feature branches back up to date with the control branch so the
`code/open-pr` staleness gate passes on relaunch.

The `coga open-pr` command fails loud when a branch is materially stale relative
to `origin/main` — correct fail-loud behavior, because a stale PR can
reintroduce reverted work, but the remedy (rebase, re-verify, force-push) is
manual per branch. This task is that remedy, run over every live branch at
once. It is the counterpart to `branch-sweep`: branch-sweep deletes branches
whose work already landed; this task rebases branches whose work is still in
flight. Neither touches the other's set.

### Scope — what counts as live

1. Every non-main branch checked out in a worktree (`git worktree list`).
2. Every `branch:` recorded under a non-terminal ticket's `## Dev` section.

Skip everything else. A stale branch with no worktree and no live ticket is
abandoned or already-merged residue — branch-sweep's problem, not this task's.

### Run order

1. **Enumerate** — `git fetch origin main`, then for each live branch check
   `git merge-base --is-ancestor origin/main <branch>`. Collect the stale
   ones; record the up-to-date ones as no-ops.
2. **Rebase** — in the branch's own worktree when it has one, otherwise in a
   temporary worktree, and only from a clean tree: a dirty worktree is
   skipped and reported, never stashed. Then `git rebase origin/main`.
3. **Conflicts** — resolve only trivial mechanical conflicts (both sides
   appended to the same list, whitespace). Anything semantic:
   `git rebase --abort`, leave the worktree exactly as found, and report the
   branch with its conflicting files.
4. **Verify** — a textually clean rebase can still be semantically wrong
   (docs describing behavior main since changed, code building on a reverted
   commit). Re-read the branch's diff against the new base; run
   `python -m pytest` when it touches `src/` or `tests/`. Report — don't
   push — a branch whose content no longer holds.
5. **Push** — `git push --force-with-lease` only for branches that already
   have an upstream; an existing PR updates automatically. Never open a PR
   here — that belongs to each ticket's own `code/open-pr` step, which now
   passes its staleness gate on relaunch.
6. **Summarize** — replace the `## Rebase Run Summary` section in this
   blackboard with one line per branch: `rebased-pushed`, `rebased-local`,
   `up-to-date`, `conflict — human needed`, `skipped-dirty`, or
   `skipped-verify-failed`, plus the `coga launch <slug>` command for any
   ticket whose open-pr step is now unblocked. Replace, don't append — the
   blackboard is composed into every launch and must stay bounded.

### Safety rules

- Never delete a branch or worktree — branch-sweep owns deletion.
- Never touch `main`; never push without `--force-with-lease`.
- Never stash, commit, or reset a dirty worktree; skip and report it.
- A worktree already mid-rebase or mid-merge at the start of the run is
  someone's live session: report it, don't touch it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Blockers

- [ ] [2026-07-23 10:30] [agent:claude] id=20260723T103037 Rebase sweep is complete and its full results are written to the parent blackboard (coga/recurring/rebase-stale-worktrees/ticket.md: ## Rebase Run Summary, base e842c8d3). Cannot record completion: 'coga mark done' trips the direct/body strand guard on product commits (docs/reference.md, src/coga/commands/megalaunch.py, src/coga/megalaunch.py, a cli SKILL twin, tests/test_megalaunch.py) that belong to the HOST checkout's branch megalaunch-pick-all-nonterminal, not to this recurring task (which touched only Coga state). The documented escape hatch 'coga mark done recurring/rebase-stale-worktrees --force' is denied by the sandbox permission classifier. ACTION NEEDED: run 'coga mark done recurring/rebase-stale-worktrees --force' yourself (safe — those files stay on their own live branch, nothing strands), or grant Bash permission for that command.
