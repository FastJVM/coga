---
title: Autoclose merged tickets
status: in_progress
mode: script
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/period-task
skills: []
workflow:
  name: autoclose-merged/sweep
  steps:
  - name: sweep
    skills:
    - relay/autoclose/sweep
    assignee: agent
step: 1 (sweep)
---

## Description

Close Relay tickets whose linked GitHub PR has already merged and whose Relay
workflow is at its final step.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `relay mark done`. Once a day this recurring task fires before
the daily digest. Its `mode: script` step runs the existing merged-ticket sweep,
which:

1. scans active and in-progress tickets,
2. reads the `pr:` line under each ticket blackboard's `## Dev` section,
3. checks the linked PR state with `gh pr view`,
4. leaves non-final-step tickets alone as suspicious, and
5. marks final-step or workflow-less tickets `done` when the PR is merged.

The sweep uses the same `relay.automerge.auto_bump_merged` function as the
manual `relay automerge` command. This recurring task only changes when the
sweep runs; it does not change which tickets are safe to close.

Done events produced by the sweep go through `relay mark done`, so they are
spooled into the daily digest when `recurring/digest/` is installed. Running at
8am keeps those closures visible in the same day's 9am digest. A quiet day with
no merged final-step tickets exits successfully and changes nothing.

## Context

