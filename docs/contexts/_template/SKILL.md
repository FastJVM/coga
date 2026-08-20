---
name: _template
description: Starter context. Copy this directory to contexts/<namespace>/<your-context>/ and replace this content. Contexts are domain knowledge — what's true about the world — and attach to tickets via the `contexts:` frontmatter list.
---

# Replace with your context title

This file follows the `SKILL.md` standard — the same format Claude Code
and OpenAI Codex use. Contexts and skills share the format on purpose:
zero proprietary extensions, and tools like Anthropic's `skill-creator`
can author and edit these files directly.

Contexts are domain knowledge. No process, no scripts. Tickets attach to
contexts via the `contexts:` field; `coga launch` inlines this file
into the prompt at launch time.

Keep contexts under a page. If you find yourself adding a fourth
top-level section, the context is conflating two domains — split it.

## Section 1

Facts the agent needs. Concrete, specific, dated when appropriate.

## Section 2

Edge cases and gotchas — things that surprise the agent.

## What this context does NOT cover

Optional but valuable. Helps prevent over-attachment to unrelated tasks.
