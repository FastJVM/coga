---
slug: recurring/resolve-conflicts
title: Resolve PR conflicts
status: active
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

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
