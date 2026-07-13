---
schedule: "0 8 * * *"
schedule_comment: "Every day at 8am - close merged final-step tickets before the 9am digest"
title: "Autoclose merged tickets"
# A script step runs the sweep directly with no agent: the workflow's one
# step references the `coga/autoclose/sweep` skill, whose `script:` calls
# `coga.autoclose.sweep_merged`. No `claude -p` / `codex exec`
# buffering, so it is safe under the temporary mode=auto recurring freeze.
mode: script
workflow: autoclose-merged/sweep
---

## Description

Close Coga tickets whose linked GitHub PR has already merged and whose Coga
workflow is at its final step.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `coga mark done`. Once a day this recurring task fires before
the daily digest. Its script step runs the existing merged-ticket sweep,
which:

1. scans active and in-progress tickets,
2. reads the `pr:` line under each ticket blackboard's `## Dev` section,
3. checks the linked PR state with `gh pr view`,
4. leaves non-final-step tickets alone as suspicious, and
5. marks final-step or workflow-less tickets `done` when the PR is merged.

This sweep is the sole trigger for auto-closing merged tickets — there is
no manual `automerge` command. The recurring task only changes when the
sweep runs; it does not change which tickets are safe to close.

Done events produced by the sweep go through `coga mark done`, so they are
spooled into the daily digest when `recurring/digest/` is installed. Running at
8am keeps those closures visible in the same day's 9am digest. A quiet day with
no merged final-step tickets exits successfully and changes nothing.

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. The
`coga/autoclose/sweep` script keeps no durable state here - every run's output
is the tickets it marks done and the resulting digest spool records.
