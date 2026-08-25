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

Keep a context as short as its domain allows, and no shorter. A
narrowly scoped context really is two or three sections and about a
page. A context that covers a large domain legitimately grows past
that — several of this repo's own contexts run to ten or more top-level
sections and tens of KB, because the domain is that big and splitting it
would just scatter one subject across directories.

Length is therefore not the test; coherence is. Split when a context
starts answering questions from two different domains, not when it
crosses a section count. If a context is long *and* incoherent, the
length is a symptom — fix the scope, not the word count.

## Section 1

Facts the agent needs. Concrete, specific, dated when appropriate.

## Section 2

Edge cases and gotchas — things that surprise the agent.

## What this context does NOT cover

Optional but valuable. Helps prevent over-attachment to unrelated tasks.
