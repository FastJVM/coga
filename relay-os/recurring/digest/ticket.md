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
Done tickets and recurring scan errors append one JSONL record to the dedicated
`spool.md` file (its `## Spool (pending)` section) — see
`relay.notification.notify`. Once a day this ticket fires on its schedule and
its script step runs `relay digest`, which:

1. reads the unconsumed Done/error records (a merge-by-construction spool, not a lock),
2. fetches `origin/main` and scans commits since `### Digest State` `last_commit`
   (first run falls back to the last 24 hours),
3. attributes merge commits to Done tickets by matching PR numbers,
4. filters Relay's own state-sync commits out of "Also merged",
5. posts one sectioned message to the shared channel,
6. advances the spool watermark, trimming the consumed prefix and keeping the
   newest record as an anchor (so a concurrent producer append never conflicts), and
7. updates `### Digest State` with the new high-water mark.

Genuinely urgent events (`relay panic`, script-step failures, the
manual `relay slack` FYI) bypass the spool and still post live, so a stuck
agent or a failure never waits a day to be seen.

An empty spool is not automatically a no-op: merged commits can still produce
the "Also merged (no ticket)" section. The run posts nothing only when there
are no Done records, no recurring errors, and no post-filter new commits. The
spool and high-water mark are real, git-tracked, human-readable state — never
hidden state — so the queue and scan boundary are always legible.

<!-- relay:blackboard -->

This blackboard holds the **git high-water state** for the daily Slack digest.
The pending-record spool lives in the sibling `spool.md` file (a `merge=union`
file kept out of this ticket so concurrent appends never touch the YAML
frontmatter); only the `### Digest State` mark below lives here, written by the
single `relay digest` consumer.

`relay recurring` keeps the serviced-period high-water mark here and append-only
human history in the repo-global `relay-os/log.md` (never composed into a run,
so it can grow unbounded).

last_serviced_period: 2026-06-17

### Digest State

last_commit: 8fe393be8ee3fd7f0e8b76ad237c144227baafa4
range: last 24h..8fe393b (123 commit(s), 16 reported)
posted: yes

## Spool (pending)

{"ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"→ done (script)","ticket":"recurring/autoclose-merged","owner":"nick"}
