---
slug: recurring/autoclose-merged
title: Autoclose merged tickets
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
period_generation: 39f8160e-82fe-455d-80d4-e184cdf13ef2
workflow:
  name: autoclose-merged/sweep
  steps:
  - name: sweep
    skills:
    - coga/autoclose/sweep
    assignee: agent
secrets: null
---

## Description

Close Coga tickets whose linked GitHub PR has already merged and whose Coga
workflow is at its final step.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `coga mark done`. Once a day this recurring task fires before
the daily digest. Its `ticket.py` runs the existing merged-ticket sweep,
which:

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

Done events produced by the sweep go through `coga mark done`, so they are
spooled into the daily digest when `recurring/digest/` is installed. Running at
8am keeps those closures visible in the same day's 9am digest. A quiet day with
no merged final-step tickets exits successfully and changes nothing.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-09-10T16:55:17+00:00
Task: `recurring/autoclose-merged`

2 auto-closed ticket(s) still have a recorded feature checkout. Autoclose never removes one — `coga retire` owns the worktree and branch safety proofs:

- `a-slack-repo-without-important-webhook-can-abort-t` "A Slack repo without important_webhook can abort the recurring scan phase": worktree `/home/n/Code/claude/coga-scan-alert-nonfatal`, branch `scan-alert-nonfatal` — `coga retire a-slack-repo-without-important-webhook-can-abort-t`
- `activation-does-not-resolve-step-1-s-assignee-role` "Activation does not resolve step 1's assignee role token": worktree `/home/n/Code/claude/coga-resolve-step-one-assignee`, branch `resolve-step-one-assignee` — `coga retire activation-does-not-resolve-step-1-s-assignee-role`
