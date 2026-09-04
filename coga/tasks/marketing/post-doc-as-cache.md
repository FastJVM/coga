---
slug: marketing/post-doc-as-cache
title: Post doc as cache
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
  - marketing/plan
  - marketing/positioning
skills:
  - marketing/write-post
workflow: null
secrets: null
---

## Description

Write launch post 3 — "documentation as cache" — per phase 3 of
`marketing/plan`: sessions are stateless, so an undocumented repo makes the
agent re-buy the same understanding every run; contexts are that
understanding bought once and composed into every prompt for free. This post
wants receipts: collect token measurements during phases 1-2 (same task with
vs without contexts; `--prompt-report`, schema-2 usage records) before
writing. Attach them to the outline or blackboard as private source evidence:
use them to test the premise and choose a concrete cached-understanding
example, but do not put their values, a delta, or a measured faster/fewer-token
claim into this essay. `marketing/plan`'s claim discipline governs that
boundary.

## Context

`marketing/write-post` is the order of work and the gates for this post; it is
attached under `skills:`. It reads the two marketing contexts for what to say
and hands the prose-craft pass to the imported `clarity` skill at
`coga/skills/clarity/SKILL.md`. Follow its steps rather than re-deriving a
process from the contexts.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
