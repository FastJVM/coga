---
slug: recurring/resolve-conflicts
title: Resolve PR conflicts
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
delegate: bootstrap/resolve-conflicts
period_generation: 5b84b908-0aad-414d-84fd-7e4b56bd4fee
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
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

The `delegate:` field above is the whole delegation. Creation freezes it into
the period ticket, so sweeps, named retries, and direct
`coga launch recurring/resolve-conflicts` never consult mutable template
dispatch. The runner marks the period task `in_progress`, launches
`bootstrap/resolve-conflicts` in-process (honouring the sweep's `--agent`
override and selected queue session conduct), and marks the period task
`done` only after the
delegated command's final `coga slack` roll-up emits its bootstrap done
sentinel. Launch preflights before the start transition, then reloads and
recomposes after that publication. Before bootstrap work, it also checks push
access for the materialized period task; the stateless bootstrap target would
otherwise skip that gate. Start publication, final spawn, and post-child
completion/timeout all lease the exact period ticket plus its task-audit
generation against control, so a later period at the same stable path cannot
receive an older child's result. Sweeps reread dispatch after reconciliation,
freeze every admitted period generation before the first child, and perform
full recurring admission at their outer boundary; each ordinary child also
refreshes and checks that exact generation immediately before launch, while
delegation fails closed on every exact-lease verification/publication error. A
direct launch requires verified catch-up before resolving even a locally missing period ref. A
natural/crashed exit fails without completing the period. A
multi-task sweep pauses a watchdog timeout and records it as timed out only
after that pause is verified on control; a stale or failed pause refuses the
run. Strict publication unwinds an unaccepted local lifecycle commit and probes
an exact remote candidate after a lost push reply; an unknown outcome retains
local reconciliation evidence rather than rolling back into split state. An
explicit named launch fails and leaves the period retryable.

The replacement intentionally covers **open PRs only**. The removed
`rebase-stale-worktrees` task also found pre-PR branches through worktrees and
ticket `branch:` lines; that extra coverage is deliberately not preserved.
For an on-demand run, call `coga resolve-conflicts` directly instead of forcing
this recurring template.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
