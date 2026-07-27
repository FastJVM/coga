---
slug: decide-the-fate-of-two-premise-dead-v2-drafts-whos
title: Decide the fate of two premise-dead v2 drafts whose subject no longer exists
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Filed by the Dream run of 2026-W31 (Phase 2 knowledge scan, finding F12, class
`stale`).

Dream does not change ticket lifecycle state on its own — cancelling a draft is a
human decision — so this finding is parked here rather than actioned.

## The problem

Two parked drafts are **premise-dead**: the thing they ask someone to document no
longer exists. Anyone who picks either one up would write prose describing a
removed design.

### 1. `coga/tasks/v2/document-parent-orchestrates-child-script-tasks-pa.md`

Asks to document "deterministic phases run as child `mode: script` tasks, each
with a one-step workflow referencing a worker skill" as the canonical
housekeeping pattern. That is the exact shape **PR #650 deleted**. Dream's
deterministic phases now invoke registered recipes directly from the parent task,
and the recipes inherit the parent's `COGA_TASK_*`.

### 2. `coga/tasks/v2/document-interactive-recurring-sweep-hazard-in-rel.md`

Is entirely about the `mode:` frontmatter field (`script` / `auto` /
`interactive`) and the two open tickets that were meant to settle it. **The field
is gone.** `coga/contexts/coga/recurring/SKILL.md` now documents the surviving
true constraint: "Agent work needs a TTY; recipes and complete scripts can be
headless."

Both were themselves prior Dream `gap` findings, which is worth noting: a gap
ticket that sits long enough can outlive its own subject.

## The decision needed

For each ticket, one of:

- **Cancel** with a reason (`coga mark canceled`), or
- **Rewrite** against the current shape. For #1 that would mean documenting the
  phase-list-plus-subagent-scan pattern in `coga/patterns` — but only if that
  pattern is actually wanted as a reusable convention. For #2 there is likely
  nothing left to salvage.

## Incidental

Both tickets, like most of `coga/tasks/v2/`, still say "relay" / `relay-os`
throughout — they predate the rename, and the paths they cite do not resolve.
That is a broader cleanup question for the whole `v2/` parking area, not just
these two.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
