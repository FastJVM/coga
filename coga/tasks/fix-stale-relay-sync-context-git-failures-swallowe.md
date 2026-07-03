---
slug: fix-stale-relay-sync-context-git-failures-swallowe
title: 'Fix stale coga/sync context: git failures swallowed (exit 0), not typer.Exit(1)'
status: active
mode: agent
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

The `coga/sync` context is stale: it still describes git task-state sync
failures as fatal (`typer.Exit(1)`), but the actual contract is that
mid-workflow sync misses (`coga bump` / `mark`) are non-fatal — reported to
stderr and `log.md`, exit 0, work continues — while only the launch-entry push
preflight is fatal (see `coga/architecture`, "launch" section). Verify the
current behavior against source first (`src/coga/` git-sync path), then update
the `coga/sync` context to describe the real fatal/non-fatal split. Check both
the live copy under `coga/contexts/` and the packaged copy under
`src/coga/resources/templates/coga/` and keep them in sync. Docs-only change —
if the source turns out to actually raise `typer.Exit(1)` somewhere the
architecture context says it shouldn't, stop and block rather than guessing
which side is right.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
