---
slug: v2/enforce-a-prompt-token-budget-in-compose
title: Enforce a prompt token budget in compose
status: draft
mode: llm
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: low/medium. Measures but never acts.

Compose computes per-layer `byte_count`/`approx_tokens` and a total
`estimate_tokens` (`compose.py:82-105`), but **nothing enforces a budget** —
no cap, no warning, no truncation. A fat context or a large blackboard simply
blows up the system prompt. The only size guard anywhere is the blackboard-size
*warning* in `validate.py:266-276`; skills and contexts have no size check at
all. This compounds with the eager full-body skill inlining (no progressive
disclosure) — see the compose-frontmatter ticket.

Add a budget the composition actually respects:
- a configurable soft cap that emits a clear warning (with the per-layer
  breakdown already available via `compose_prompt_report`) when exceeded
- optionally a hard cap that fails loud rather than silently shipping an
  oversized prompt
- decide whether oversize is a launch-blocking error or a warning (lean: warn by
  default, configurable to block)

Also replace / clearly caveat the `chars/4` `estimate_tokens` heuristic
(`compose.py:101-105`) — fine as a gauge, misleading as a budget input.

Acceptance: a composition that exceeds the configured budget produces a clear,
actionable message (per-layer breakdown), not a silent oversized prompt; tested.

## Context

Code: `src/relay/compose.py` (`PromptComposition` 82-86, `estimate_tokens`
101-105, the per-layer accounting feeding `compose_prompt_report`),
`src/relay/validate.py:266-276` (blackboard-only size check today). Related:
`measure-relay-prompt-scope-and-agent-precision` (measurement) and the compose-
frontmatter ticket (eager inlining).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
