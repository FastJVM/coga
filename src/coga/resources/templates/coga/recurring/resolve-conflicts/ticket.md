---
schedule: "0 8 * * 1"
schedule_comment: "Every Monday at 8am — after branch-sweep, resolve conflicts on open PRs"
title: "Resolve PR conflicts"
delegate: bootstrap/resolve-conflicts
# `delegate:` keeps this template agent-backed for admission — a headless
# sweep refuses it before the period task exists — while `coga recurring`
# launches the bootstrap target directly in the operator's terminal, under the
# sweep's idle/max-session liveness bounds. No agent session runs on the
# period task itself, so nothing here shells out to a nested `coga launch`.
---

## Description

Run the stateless `coga resolve-conflicts` command once a week, after
`branch-sweep` has pruned merged branch residue.

This recurring entry owns only the schedule. The command ticket under
`bootstrap/resolve-conflicts` owns the operation: enumerate open PRs, rebase
conflicting heads onto `origin/main`, resolve semantic conflicts with agent
judgment, verify before an explicit lease-safe force-push, print one line per
PR, and post the final Slack roll-up.

The `delegate:` field above is the whole delegation. The sweep marks this
period task `in_progress`, launches `bootstrap/resolve-conflicts` in-process
(honouring the sweep's `--agent` override and queue guidance), and marks the
period task `done` only after the delegated command's final `coga slack`
roll-up emits its bootstrap done sentinel. A natural/crashed exit fails
without completing the period. A multi-task sweep pauses a watchdog timeout
and continues; an explicit named launch fails and leaves the period retryable.

The replacement intentionally covers **open PRs only**. The removed
`rebase-stale-worktrees` task also found pre-PR branches through worktrees and
ticket `branch:` lines; that extra coverage is deliberately not preserved.
For an on-demand run, call `coga resolve-conflicts` directly instead of forcing
this recurring template.

<!-- coga:blackboard -->

`coga recurring` keeps the serviced-period high-water mark in the
repo-global log. Run results remain stateless: stdout plus the command's
one-line Slack roll-up, never this blackboard.
