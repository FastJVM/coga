---
name: _template
description: Starter context. Copy this directory to contexts/<namespace>/<your-context>/ and replace this content. Contexts are domain knowledge — what's true about the world — and attach to tickets via the `contexts:` frontmatter list.
---

# Replace with your context title

Contexts are domain knowledge. No process, no scripts. Tickets attach to
contexts via the `contexts:` field; `relay launch` inlines this file
into the prompt at launch time.

Keep contexts under a page. If you find yourself adding a fourth
top-level section, the context is conflating two domains — split it.

## Section 1

Facts the agent needs. Concrete, specific, dated when appropriate.

## Section 2

Edge cases and gotchas — things that surprise the agent.

## What this context does NOT cover

Optional but valuable. Helps prevent over-attachment to unrelated tasks.
