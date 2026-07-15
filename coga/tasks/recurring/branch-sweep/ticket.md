---
slug: recurring/branch-sweep
title: Branch sweep
status: in_progress
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: branch-sweep/sweep
  steps:
  - name: sweep
    skills:
    - coga/branch-sweep/sweep
    assignee: agent
secrets: null
script: null
step: 1 (sweep)
---

## Description

Delete local and remote git branches whose work has already landed, as the
safety net behind `coga retire`'s branch deletion.

`coga retire` deletes a finished ticket's branch immediately, but that
cleanup is best-effort — `git`/`gh` failures are swallowed there, and a
branch also leaks when a ticket is deleted without going through retire, or
a session dies mid-flight. Retire covers the common path daily (in effect,
every time a ticket finishes); this sweep runs weekly to catch what leaks
past it.

Once a week this recurring task's script step runs the branch sweep, which:

1. enumerates every local branch and every `origin` branch,
2. skips `main`, the checked-out branch, and any branch recorded under a
   not-`done` ticket's `## Dev` `branch:` line,
3. for the rest, checks GitHub by head branch name and current tip SHA —
   deletes only when a merged PR exists for that exact tip and no PR is
   currently open for the head branch, and
4. deletes the remote ref and/or local branch per the same policy
   `coga retire` uses (prefer `git branch -d`; log the tip SHA and force
   with `-D` for the squash-merge case; skip and report anything unmerged
   with no merged PR).

The sweep is defined in `coga.branchsweep.sweep_branches`. Its first run
also prunes the merged part of the branch backlog that accumulated before
retire-time deletion shipped — abandoned no-PR branches are skipped and
reported by design, so expect a residual manual pass rather than a fully
clean slate.

Because the runnable unit is the workflow + script skill
(`branch-sweep/sweep`), this sweep runs three ways: on this schedule via
`coga recurring`, on demand via `coga recurring launch branch-sweep`, or as
a standalone one-off ticket that sets `workflow: branch-sweep/sweep`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
