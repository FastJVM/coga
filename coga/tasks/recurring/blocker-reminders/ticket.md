---
slug: recurring/blocker-reminders
title: Blocker reminders
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: blocker-reminders/run
  steps:
  - name: remind
    skills:
    - coga/blockers/remind
    assignee: agent
secrets: null
---

## Description

Remind owners about tasks stopped by `coga block`.

Agents stop through `coga block`, which appends an unresolved ask under
`## Blockers` and moves the ticket to `status: blocked`. The human answer
handshake stays command-owned: run `coga unblock <slug> --answer "..."`, then
launch or megalaunch can resume the task from the files.

Once a day this recurring recipe scans ordinary tasks, including recurring
period tasks, whose frontmatter says `status: blocked`. For each unresolved
blocker that has not already been reminded, it:

1. posts a live owner reminder naming the blocked task and the canonical
   `coga unblock <slug> --answer "..."` command shape,
2. writes a compact `## Blocker reminders` watermark on the blocked task's own
   blackboard, keyed by the blocker fingerprint, and
3. syncs the changed blocked task state through git.

The reminder state lives on the blocked task, not on this recurring task, so it
travels with the ask and stays inspectable in the same file a human edits to
answer it. The reminder job does not launch, unblock, or otherwise change task
selection; it only makes unresolved asks visible again.

## Context

<!-- coga:blackboard -->

## Run 2026-08-24 — sweep clean, 0 reminders posted

Period serviced: `2026-08-24` (newest `created recurring/blocker-reminders for
<period>` line in `coga/log.md`).

Ran the deterministic sweep with `coga run blocker-reminders` (this period task
directory had no `ticket.py` sibling, so the recipe was invoked directly through
the registered `coga run` name — same entrypoint `ticket.py` calls).

Output: `[blockers] no unresolved blockers to remind.` exit 0.

Two tasks are `status: blocked`, and both unresolved asks were already
watermarked, so nothing was posted and no blocked-task file changed:

| task | blocker opened | fingerprint | last_reminded |
| --- | --- | --- | --- |
| `unblock-rewind` | 2026-08-13 22:51 (agent:codex) | `9ce2d8481594` | 2026-08-14 10:59 |
| `verify-the-pr-review-comment-loop-once-the-review` | 2026-08-20 11:24 (agent:claude) | `3023242c0745` | 2026-08-21 11:54 |

Observation for the owner (no change made — outside this run's scope): the
watermark is a permanent dedup key, not a cooldown. `remind_blocked_tasks`
skips any fingerprint already present in `## Blocker reminders`, so each
blocker gets exactly **one** reminder over its whole lifetime. `unblock-rewind`
has been blocked 11 days on a single reminder from 2026-08-14. That matches the
ticket body as written ("has not already been reminded"), so it is by design
rather than a defect — but if the intent is recurring visibility, the watermark
would need to become a re-remind interval. Worth a separate ticket if so.

No cross-run state to persist: dedup state lives on each blocked task, as the
parent blackboard records.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: Blocker reminders fire exactly once per blocker, never on an interval
