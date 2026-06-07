---
title: '[debug] Daily digest'
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
  name: digest/post
  steps:
  - name: flush
    skills:
    - relay/digest/flush
    assignee: agent
step: 1 (flush)
---

## Description

Flush the day's spooled state-change events into a single Slack digest.

Routine state-change chatter (`relay draft`/`create`, `bump`, `mark
active/paused/done`, `retire`, automerge done, recurring scaffolds) no longer
posts to Slack the moment it happens. Instead each event appends one JSONL
record to this recurring task's own `blackboard.md` (the `## Spool (pending)`
section) — see `relay.slack.notify`. Once a day this ticket fires on its
schedule and its `mode: script` step runs `relay digest`, which:

1. drains the pending records (single-process serialization, not a lock),
2. groups them **project → person → ticket** (owners pinged via `<@ID>`,
   watchers cc'd exactly as a live post would),
3. posts one sectioned message to the shared channel, and
4. empties the spool section back to its seed.

Genuinely urgent events (`relay panic`, `mode: script` step failures, the
manual `relay slack` FYI) bypass the spool and still post live, so a stuck
agent or a failure never waits a day to be seen.

An empty spool is a silent no-op: a quiet day posts nothing, and a same-day
re-run posts nothing. The spool is a real, git-tracked, human-readable
blackboard — never hidden state — so the pending queue is always legible.

## Context

