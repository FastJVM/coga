---
schedule: "0 2 * * *"
schedule_comment: "Every day at 2am - attempt launchable active agent work"
title: "Megalaunch active tickets"
workflow: megalaunch/run
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

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. The
`coga/megalaunch/run` script replaces `## Megalaunch Run Summary` each run
and leaves durable decisions or unresolved blockers in their own sections.
