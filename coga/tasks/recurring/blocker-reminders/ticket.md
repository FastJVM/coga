---
slug: recurring/blocker-reminders
title: Blocker reminders
status: done
owner: nick
human: nick
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
script: null
---

## Description

Remind owners about tasks stopped by `coga block`.

Agents stop through `coga block`, which appends an unresolved ask under
`## Blockers` and moves the ticket to `status: blocked`. The human answer
handshake stays command-owned: run `coga unblock <slug> --answer "..."`, then
launch or megalaunch can resume the task from the files.

Once a day this recurring script scans ordinary tasks, including recurring
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
