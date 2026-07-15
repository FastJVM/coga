---
slug: recurring/rebase-stale-worktrees
title: Rebase stale worktrees
status: done
owner: nick
human: nick
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
---

## Description

Bring live feature branches back up to date with the control branch so the
`code/open-pr` staleness gate passes on relaunch.

The open-pr script step fails loud when a branch is materially stale relative
to `origin/main` — correct fail-loud behavior, because a stale PR can
reintroduce reverted work, but the remedy (rebase, re-verify, force-push) is
manual per branch. This task is that remedy, run over every live branch at
once. It is the counterpart to `branch-sweep`: branch-sweep deletes branches
whose work already landed; this task rebases branches whose work is still in
flight. Neither touches the other's set.

### Scope — what counts as live

1. Every non-main branch checked out in a worktree (`git worktree list`).
2. Every `branch:` recorded under a not-`done` ticket's `## Dev` section.

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

## Run notes (2026-W29)

Enumerate done:
- 20 non-main worktree branches found; ALL are stale vs origin/main (1da0a296).
  All worktrees clean, none mid-rebase/merge. None have an upstream, so no
  pushes this run — best outcome per branch is `rebased-local`.
- 6 branches recorded under not-done tickets' `## Dev` exist neither locally
  nor on origin: codex/auto-persist-launch-dirt, codex/relay-prompt-scope-report,
  codex/write-real-coga-documentation, dev-testing-contract,
  refuse-blackboard-synthesis, retire-deletes-branch. Nothing to rebase;
  reporting as missing.

Rebase phase done:
- 3 rebased clean (docs-cleanup, megalaunch-usage-probe,
  move-read-views-to-views-module) — but all their commits were dropped as
  already-applied, so the branches are now empty vs main. Nothing to verify
  (no diff) or push (no upstream).
- 17 hit conflicts; every one inspected or clearly multi-module semantic —
  none trivially mechanical. All aborted with `git rebase --abort`; final
  sweep confirmed all 20 worktrees clean and not mid-op.
- Several small conflicts showed main already carrying an evolved version of
  the branch's change (docs-sandbox-dev-loop-friction, docs-with-review-workflow,
  fix-control-branch-mismatch-guidance, sync-context-nonfatal-git,
  warn-version-skew) — flagged as likely superseded in the summary.

`## Rebase Run Summary` written to parent blackboard
(coga/recurring/rebase-stale-worktrees/ticket.md). No open-pr step unblocked
this run. Marking done.

## Usage

{"agent":"claude","cache_creation_input_tokens":194346,"cache_read_input_tokens":3036035,"cli":"claude","input_tokens":103,"model":"claude-fable-5","output_tokens":45389,"provider":"anthropic","schema":1,"session_id":"e8e50dc0-cfe8-48e1-b3f5-8e1f973b90ca","slug":"recurring/rebase-stale-worktrees","step":"execute","title":"Rebase stale worktrees","ts":"2026-07-15T19:32:26.380304Z","usage_status":"ok"}
