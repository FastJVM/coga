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

Do not start until `marketing/token-receipts` holds at least four valid pairs
from phases 1–2 and one exact cached question is attached here as working
source support. Use the receipts to test and ground the premise, never as
publishable results: no values, delta, multiplier, or measured "faster" /
"fewer tokens" claim belongs in the essay. If the receipts contradict the
premise, narrow or replace the claim. This ticket remains an idea essay and
does not become the archived proof post.

## Context

`marketing/write-post` is the order of work and the gates for this post; it is
attached under `skills:`. It reads the two marketing contexts for what to say
and hands the prose-craft pass to the imported `clarity` skill at
`coga/skills/clarity/SKILL.md`. Follow its steps rather than re-deriving a
process from the contexts.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
