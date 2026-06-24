---
slug: retire-the-duplicate-relay-clone-so-one-process-wr
title: Retire the duplicate relay clone so one process writes state to origin
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Operational, not code: today's state-plane contention on `origin/main` came
from **two clones on one machine** racing the same ticket transitions —
`~/Code/claude/relay` and `~/Code/relay`, the latter running `relay launch
…recurring…`. Stop the second clone's recurring run (or otherwise ensure a
single control-writer) so only one process pushes state to the shared origin,
removing the live contention source independent of the code-level fix.

Decide and document: which clone owns recurring/digest scheduling, and how to
prevent a stray second clone from re-introducing the race.

## Context

Split out of `prevent-autostash-spool-conflicts-on-control-branc` (see its
blackboard). The spool-merge + rebase-hardening fix makes the race *safe* when
it happens; this ticket removes the source so it stops happening at all.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
