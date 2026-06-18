---
title: Daily digest
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

Post a single Slack digest focused on outcomes: Done tickets from the spool
plus other commits merged to `origin/main` since the last digest run.

Routine lifecycle chatter (`relay draft`/`create`, message-less `bump`, `mark
active/paused`, `retire`, successful recurring creates) does not enter Slack.
Done tickets and recurring scan errors append one JSONL record to this recurring
task's own `blackboard.md` (the `## Spool (pending)` section) — see
`relay.notification.notify`. Once a day this ticket fires on its schedule and its
`mode: script` step runs `relay digest`, which:

1. reads the pending Done/error records (single-process serialization, not a lock),
2. fetches `origin/main` and scans commits since `### Digest State` `last_commit`
   (first run falls back to the last 24 hours),
3. attributes merge commits to Done tickets by matching PR numbers,
4. filters Relay's own state-sync commits out of "Also merged",
5. posts one sectioned message to the shared channel,
6. empties the spool section back to its seed, and
7. updates `### Digest State` with the new high-water mark.

Genuinely urgent events (`relay panic`, `mode: script` step failures, the
manual `relay slack` FYI) bypass the spool and still post live, so a stuck
agent or a failure never waits a day to be seen.

An empty spool is not automatically a no-op: merged commits can still produce
the "Also merged (no ticket)" section. The run posts nothing only when there
are no Done records, no recurring errors, and no post-filter new commits. The
spool and high-water mark are real, git-tracked, human-readable blackboard
state — never hidden state — so the queue and scan boundary are always legible.

## Context

