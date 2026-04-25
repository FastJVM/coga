---
name: your-namespace/your-context
description: One sentence describing the slice of the world this context covers. Tickets attach to it via the `contexts:` field.
---

# Your context

A context is **domain knowledge** — what's true about the world the task
operates in. No process, no scripts. Pure knowledge.

Contexts attach to **tickets** (not workflow steps). They're composed
into the prompt at launch time so the agent picks up the task with the
relevant background already loaded.

## Scope

What this context covers and — equally important — what it doesn't.
Long contexts (more than a page) usually mean two contexts have been
conflated; split before that happens.

## Facts the agent needs

Bullet points or short paragraphs. Concrete, specific, dated when
appropriate. Cite sources when citing matters.

## Edge cases / gotchas

Things that surprise the agent — payment retry timing, rate-limit
behavior, vendor-specific quirks, undocumented conventions.

## What this context does NOT cover

(Optional but valuable.) Helps prevent agents from over-attaching this
context to unrelated tasks.
