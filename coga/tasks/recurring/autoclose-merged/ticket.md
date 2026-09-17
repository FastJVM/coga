---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: fb0aee06-f5f8-4169-b63c-d0f18ba23fcb
workflow:
  name: autoclose-merged/sweep
  steps:
  - name: sweep
    skills:
    - coga/autoclose/sweep
    assignee: agent
---

## Description

Close Coga tickets whose linked GitHub PR has already merged and whose Coga
workflow is at its final step.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `coga mark done`. Once a day this recurring task fires. Its
`ticket.py` runs the existing merged-ticket sweep, which:

1. scans active and in-progress tickets,
2. reads the `pr:` line under each ticket blackboard's `## Dev` section,
3. checks the linked PR state with `gh pr view`,
4. leaves non-final-step tickets alone as suspicious, and
5. marks final-step or workflow-less tickets `done` when the PR is merged, and
6. names the `coga retire` follow-up for each ticket it closed that still
   records a `branch:` or `worktree:`.

Autoclose never disposes of a checkout itself — `coga retire` owns those safety
proofs. Without step 6 an auto-closed ticket's worktree and branch outlive it
silently. Dream preserves checkout-bearing done tickets rather than deleting
the `## Dev` evidence the named command needs, so that debt stays actionable
until a human retires it.

This sweep is the sole trigger for auto-closing merged tickets — there is
no manual `automerge` command. The recurring task only changes when the
sweep runs; it does not change which tickets are safe to close.

Done events produced by the sweep go through the shared `mark_done` finalizer,
so each closure posts live to Slack exactly as a manual `coga mark done` would.
A quiet day with no merged final-step tickets exits successfully and changes
nothing.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-09-17T18:02:04+00:00
Task: `recurring/autoclose-merged`

6 auto-closed ticket(s) still have a recorded feature checkout. Autoclose never removes one — `coga retire` owns the worktree and branch safety proofs:

- `autofix/stop-one-failing-ticket-py-from-starving-the-rest` "Stop one failing ticket.py from starving the rest of the sweep": worktree `/home/n/Code/claude/coga-sweep-abandoned-record`, branch `sweep-abandoned-record` — `coga retire autofix/stop-one-failing-ticket-py-from-starving-the-rest`
- `branch-sweep-strands-squash-merged-branches-whose` "Branch sweep strands squash-merged branches whose tip moved": worktree `/home/n/Code/claude/coga-branch-sweep-landed`, branch `branch-sweep-landed` — `coga retire branch-sweep-strands-squash-merged-branches-whose`
- `dream-2026-w38-extract-backlog-4-findings-phase-4` "Dream 2026-W38 extract backlog: 4 findings Phase 4 could not consume": worktree `/home/n/Code/claude/coga-dream-w38-extract-backlog`, branch `dream-w38-extract-backlog` — `coga retire dream-2026-w38-extract-backlog-4-findings-phase-4`
- `recurring-sweep-aborts-and-orphans-a-deleted-done` "Recurring sweep aborts and orphans a deleted done period task when a template's workflow is missing": worktree `/home/n/Code/claude/coga-recurring-missing-workflow`, branch `recurring-missing-workflow` — `coga retire recurring-sweep-aborts-and-orphans-a-deleted-done`
- `the-autofix-analyst-ticket-closed-without-shipping` "The autofix analyst ticket closed without shipping any of its three defects": worktree `/home/n/Code/claude/coga-autofix-analyst-fixes`, branch `autofix-analyst-fixes` — `coga retire the-autofix-analyst-ticket-closed-without-shipping`
- `title-only-tickets-have-no-convention-and-no-valid` "Title-only tickets have no convention and no validator": worktree `/home/n/Code/claude/coga-title-only-validator`, branch `title-only-validator` — `coga retire title-only-tickets-have-no-convention-and-no-valid`
