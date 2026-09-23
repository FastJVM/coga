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
into the prompt at launch time. That makes a context *eager* knowledge,
paid for on every launch that attaches it. A link to another context or
page is navigation only — it never loads that page — so a task that needs
another topic must attach it too. One owner per fact: before copying text
from a doc or another context, read `coga/knowledge` (attach that ref to the
authoring ticket to load the rule; Coga resolves it from the configured
contexts directory or the bundled package).

Keep one topic per context, sized for selective attachment: aim for
60-160 lines and roughly 500-1,500 tokens (characters / 4). Review a
context that passes 200 lines, 10,000 bytes, or 2,500 tokens — check all
three — and split it into focused sibling topics rather than letting one
file answer several readers' questions. An overview that links its
children should stay under about 1,000 tokens. A context kept larger needs
a stated reason.

## Section 1

Facts the agent needs. Concrete, specific, dated when appropriate.

## Section 2

Edge cases and gotchas — things that surprise the agent.

## What this context does NOT cover

Optional but valuable. Helps prevent over-attachment to unrelated tasks.
