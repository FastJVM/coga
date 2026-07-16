---
schedule: "0 9 * * *"
schedule_comment: "Every day at 9am — post one Slack digest of Done tickets and merged commits"
title: "Daily digest"
# A script step runs the flush directly with no agent: the workflow's one
# step references the `coga/digest/flush` skill, whose `script:` runs
# `coga digest`. It runs directly with no agent buffering, so it is safe for
# unattended recurring runs.
workflow: digest/post
owner: nicktoper
assignee: claude
---

## Description

Post a single Slack digest focused on outcomes: Done tickets from the spool
plus other commits merged to `origin/main` since the last digest run.

Routine lifecycle chatter (`coga create`, message-less `bump`, `mark
active/paused`, `retire`, successful recurring creates) does not enter Slack.
Done tickets and recurring scan errors append one JSONL record to the dedicated
`spool.md` file (its `## Spool (pending)` section) — see
`coga.notification.notify`. Once a day this ticket fires on its schedule and
its script step runs `coga digest`, which:

1. reads the unconsumed Done/error records (a merge-by-construction spool, not a lock),
2. fetches `origin/main` and scans commits since `### Digest State` `last_commit`
   (first run falls back to the last 24 hours),
3. attributes merge commits to Done tickets by matching PR numbers,
4. filters Coga's own state-sync commits out of "Also merged",
5. posts one sectioned message to the shared channel,
6. advances the spool watermark, trimming the consumed prefix and keeping the
   newest record as an anchor (so a concurrent producer append never conflicts), and
7. updates `### Digest State` with the new high-water mark.

Genuinely urgent events (`coga block`, script-step failures, the
manual `coga slack` FYI) bypass the spool and still post live, so a stuck
agent or a failure never waits a day to be seen.

An empty spool is not automatically a no-op: merged commits can still produce
the "Also merged (no ticket)" section. The run posts nothing only when there
are no Done records, no recurring errors, and no post-filter new commits. The
spool and high-water mark are real, git-tracked, human-readable state — never
hidden state — so the queue and scan boundary are always legible.

<!-- coga:blackboard -->

This blackboard holds the **git high-water state** for the daily Slack digest.
The pending-record spool lives in the sibling `spool.md` file (a `merge=union`
file kept out of this ticket so concurrent appends never touch the YAML
frontmatter); only the `### Digest State` mark below lives here, written by the
single `coga digest` consumer.

`coga recurring` keeps the serviced-period high-water mark here and append-only
human history in the repo-global `coga/log.md` (never composed into a run,
so it can grow unbounded).

last_serviced_period: 2026-07-16

### Digest State

last_commit: 074c205e405c43463bcda9c0c16b4290237faee9
range: 20979cd..074c205 (121 commit(s), 16 reported)
posted: yes
