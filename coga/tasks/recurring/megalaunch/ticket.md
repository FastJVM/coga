---
slug: recurring/megalaunch
title: Megalaunch active tickets
status: active
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: megalaunch/run
  steps:
  - name: run
    skills:
    - coga/megalaunch/run
    assignee: agent
secrets: null
script: null
step: 1 (run)
---

## Description

Attempt launchable active Coga work owned by the configured current user
sequentially. This is a script-backed recurring task, not a parallel agent
fanout: it calls the shared megalaunch engine used by `coga megalaunch`,
filters out tickets whose `owner` is not `load_config().current_user` so other
owners' work is not launched or counted as skip noise, checks each assigned
agent's budget guard before launching, and stops or skips conservatively when
work is blocked, human-owned, over budget, or fails a launch preflight. The
engine spawns each step as a normal interactive launch under the PTY watcher,
so it requires a TTY — a headless scheduled run fails loud (exit 2) instead of
launching silent agents.

Each run writes one compact `## Megalaunch Run Summary` section to its
blackboard with counts and per-ticket outcomes. The summary is replaced on
rerun so old per-run noise does not accumulate in future prompts; unresolved
blockers stay on the affected task blackboards.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
