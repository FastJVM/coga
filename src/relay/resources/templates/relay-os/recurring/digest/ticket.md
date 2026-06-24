---
schedule: "0 9 * * *"
schedule_comment: "Every day at 9am — post one Slack digest of Done tickets and merged commits"
title: "Daily digest"
# A script step runs the flush directly with no agent: the workflow's one
# step references the `relay/digest/flush` skill, whose `script:` runs
# `relay digest`. No `claude -p` / `codex exec` buffering, so it is safe under
# the temporary mode=auto recurring freeze.
autonomy: auto
workflow: digest/post
owner: nick
assignee: claude
---

## Description

Post a single Slack digest focused on outcomes: Done tickets from the spool
plus other commits merged to `origin/main` since the last digest run.

Routine lifecycle chatter (`relay create`, message-less `bump`, `mark
active/paused`, `retire`, successful recurring creates) does not enter Slack.
Done tickets and recurring scan errors append one JSONL record to this recurring
task's own `blackboard.md` (the `## Spool (pending)` section) — see
`relay.notification.notify`. Once a day this ticket fires on its schedule and its
The script step runs `relay digest`, which:

1. reads the pending Done/error records (single-process serialization, not a lock),
2. fetches `origin/main` and scans commits since `### Digest State` `last_commit`
   (first run falls back to the last 24 hours),
3. attributes merge commits to Done tickets by matching PR numbers,
4. filters Relay's own state-sync commits out of "Also merged",
5. posts one sectioned message to the shared channel,
6. empties the spool section back to its seed, and
7. updates `### Digest State` with the new high-water mark.

Genuinely urgent events (`relay panic`, script-step failures, the
manual `relay slack` FYI) bypass the spool and still post live, so a stuck
agent or a failure never waits a day to be seen.

An empty spool is not automatically a no-op: merged commits can still produce
the "Also merged (no ticket)" section. The run posts nothing only when there
are no Done records, no recurring errors, and no post-filter new commits. The
spool and high-water mark are real, git-tracked, human-readable blackboard
state — never hidden state — so the queue and scan boundary are always legible.

<!-- relay:blackboard -->

This blackboard is the **spool and git high-water state** for the daily Slack
digest.

Done outcomes and recurring scan errors append one JSONL record to the
`## Spool (pending)` section below as they happen (see `relay.notification.notify`).
The daily `relay digest` run combines those records with a git scan of
`origin/main`, posts one outcome-focused message to Slack, empties the spool
back to just the heading, and updates `### Digest State`. Everything here is
plain text in a git-tracked file on purpose — the pending queue and high-water
mark stay legible, never hidden state.

`relay recurring` keeps the serviced-period high-water mark here and append-only
human history in this template's `log.md` (never composed into a run, so it can
grow unbounded). The digest flush still parses only valid JSON records and
rewrites only the spool section, so any stray non-JSON line is left untouched.

### Digest State

last_commit:
range:
posted:

## Spool (pending)
