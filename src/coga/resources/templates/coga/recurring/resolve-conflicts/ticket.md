---
schedule: "0 8 * * 1"
schedule_comment: "Every Monday at 8am — after branch-sweep, resolve conflicts on open PRs"
title: "Resolve PR conflicts"
# This template is a thin scheduled wrapper around the stateless, agent-backed
# command ticket. The inline script deliberately performs no git work itself;
# it enters the normal command alias so the command ticket remains the one
# durable definition of scope, safety, verification, reporting, and judgment.
script: inline
---

## Description

Run the stateless `coga resolve-conflicts` command once a week, after
`branch-sweep` has pruned merged branch residue.

This recurring entry owns only the schedule. The command ticket under
`bootstrap/resolve-conflicts` owns the operation: enumerate open PRs, rebase
stale heads onto `origin/main`, resolve semantic conflicts with agent judgment,
verify before an explicit lease-safe force-push, print one line per PR, and post
the final Slack roll-up. The inline script below launches that agent-backed
command through the ordinary alias with queue guidance so a scheduled run
announces its plan and proceeds without waiting for confirmation; it does not
duplicate the runbook.

The replacement intentionally covers **open PRs only**. The removed
`rebase-stale-worktrees` task also found pre-PR branches through worktrees and
ticket `branch:` lines; that extra coverage is deliberately not preserved.
For an on-demand run, call `coga resolve-conflicts` directly instead of forcing
this recurring template.

## Script

```bash
exec coga resolve-conflicts --queue-guidance
```

<!-- coga:blackboard -->

`coga recurring` keeps the serviced-period high-water mark here as
`last_serviced_period`. Run results remain stateless: stdout plus the command's
one-line Slack roll-up, never this blackboard.
