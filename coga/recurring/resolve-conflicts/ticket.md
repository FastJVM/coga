---
schedule: "0 8 * * 1"
schedule_comment: "Every Monday at 8am — after branch-sweep, resolve conflicts on open PRs"
title: "Resolve PR conflicts"
# This template stays agent-backed so recurring's TTY admission, selected-agent
# override, idle timeout, and max-session watchdog govern the whole delegated
# command. The command ticket remains the one durable operational runbook.
---

## Description

Run the stateless `coga resolve-conflicts` command once a week, after
`branch-sweep` has pruned merged branch residue.

This recurring entry owns only the schedule. The command ticket under
`bootstrap/resolve-conflicts` owns the operation: enumerate open PRs, rebase
conflicting heads onto `origin/main`, resolve semantic conflicts with agent
judgment, verify before an explicit lease-safe force-push, print one line per
PR, and post the final Slack roll-up.

Delegate through the ordinary command alias; do not reproduce or improvise a
second runbook here:

1. Run `coga resolve-conflicts --agent <current-agent-type>`, replacing the
   placeholder with the configured Coga agent type running this wrapper
   (normally `claude` or `codex`). This preserves an explicit recurring
   `--agent` override for the command that performs the conflict work.
2. If this launch includes automatic queue guidance, also pass
   `--queue-guidance`; omit it for an interactive recurring launch. Wait for
   the delegated command to return. Recurring's outer agent supervisor remains
   responsible for TTY admission and the idle/max-session liveness bounds over
   the whole process tree.
3. After a successful delegated run, finish this period task with
   `coga mark done recurring/resolve-conflicts`. Surface a delegated failure;
   do not mark the period task done as if the sweep succeeded.

The replacement intentionally covers **open PRs only**. The removed
`rebase-stale-worktrees` task also found pre-PR branches through worktrees and
ticket `branch:` lines; that extra coverage is deliberately not preserved.
For an on-demand run, call `coga resolve-conflicts` directly instead of forcing
this recurring template.

<!-- coga:blackboard -->

`coga recurring` keeps the serviced-period high-water mark here as
`last_serviced_period`. Run results remain stateless: stdout plus the command's
one-line Slack roll-up, never this blackboard.

last_serviced_period: 2026-W29
