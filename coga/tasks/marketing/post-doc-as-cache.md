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

Write and ship launch post 3 — **productivity, by mechanism** — per phase 3 of
`marketing/plan`. Sessions are stateless, so an undocumented repo makes an
agent reconstruct the same understanding every run; contexts turn
documentation into a cache of human judgment.

Before drafting, link the exact public context, the question it answers, and
a later session's record showing that understanding in use. Begin with the
selected examples from `marketing/plan/collect-public-examples-for-the-launch`;
report a missing second half instead of inventing reuse. The ordinary phase
and owner gates in `marketing/plan` still apply.

The owner dropped the paired token/time experiment on 2026-09-09. No paired
runs, receipt quota, or token-measurement ticket is required. This remains an
idea essay: do not claim a measured saving, a productivity multiplier, or
generality from a single example. If the source contradicts the mechanism,
narrow or replace the claim.

## Context

`marketing/write-post` is the order of work and the gates for this post; it is
attached under `skills:`. It reads the two marketing contexts for what to say
and hands the prose-craft pass to the imported `clarity` skill at
`coga/skills/clarity/SKILL.md`. Follow its steps rather than re-deriving a
process from the contexts.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
