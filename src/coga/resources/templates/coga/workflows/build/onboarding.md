---
name: build/onboarding
description: First-run onboarding — one scripted question, an agent-led chat, a signed-off vision, and a flat batch of launchable draft tickets. Empty repos only; no scan.
steps:
  - name: gather-and-spec
    assignee: agent
  - name: generate-batch
    assignee: agent
---

## gather-and-spec

This is the user's first run after `coga init`. `coga init` already captured
their name, so `current_user` is valid — do **not** re-prompt for it. There is
nothing to scan (this flow is empty-repo only); intent comes from the user, not
the repo.

Ask one scripted question and let the conversation do the rest:

> **What do you want to build?**

Then run an agent-led chat of **at most two follow-ups**. Spend them only on
*shape-defining* unknowns — the kind that change what the project is or what v1
includes (CLI vs web app, who it's for, is-X-in-scope-for-v1). Do **not** chase
detail or decision unknowns (which library, which provider, the exact formula);
those are not yours to settle here. Draw intent out; don't interrogate.

Draft a short **vision** — a few sentences covering *what* / *who* / *what
success looks like*, plus the v1 scope shape — and present it **in the same
turn** for sign-off. There is no separate review step: take the user's
confirmation here, in chat. When you present it, name the decisions you
deliberately deferred (they become "decide/evaluate X" ticket candidates in the
next step) so the deferral is visible; the user may pull a genuinely
shape-defining one back into the chat.

Never fabricate. If something you'd need is missing, stub it and ask — don't
invent a fact to fill the gap.

On sign-off:

- Write the agreed vision to **`coga/contexts/product/vision/SKILL.md`** in
  this repo: valid `SKILL.md` frontmatter, the few sentences above as the body.
  Frame it as a living starter doc the owner edits as the project evolves, not a
  finished spec.
- Keep raw intake and working notes on the blackboard, not in the context.
- `coga bump`.

## generate-batch

Read the vision context you just wrote (and the blackboard notes). Generate a
batch of draft tickets the user can launch — the durable vision is what each
ticket is generated from, so a later `coga launch <slug>` is oriented by the
product without re-stating it.

Rules for the batch:

- Generate **as many tickets as the vision genuinely supports** — build tickets
  plus a *subset* of "decide/evaluate X" tickets for the deferred decisions. No
  padding to a number, no truncating real work, no count cap (it's usually a
  handful). Keep the "decide/evaluate X" tickets a subset, not the bulk.
- Each ticket is a **draft** (`status: draft`), has a thin what+why body, and
  lists the vision context in its frontmatter (`contexts: [product/vision]`).
- **No pre-chosen anchor, no ordering, no grouping, no recommendation.** Which
  ticket to run first is the user's call — they have context you don't. Present
  one flat list (slug + one line each, neutral order); don't rank, don't bucket
  (not even "build" vs "decision"), don't suggest a starting point.

Create each ticket as a **bare draft, non-interactively** — do not launch a
per-ticket authoring interview. The capability this step depends on is
non-interactive bulk draft creation, which ships today via `create_task`
(surfaced as `coga create <slug>`); if/when `coga ticket` consolidates
creation (`marketing/coga-ticket-creates`), use `coga ticket <slug>` instead.
The command name is the only thing that changes — this step does not block on
that ticket.

End in chat (no separate approval step): present the flat list, get the user's
approval, then hand over the generic launch command — e.g. "Here's your starter
batch — launch any one with `coga launch <ticket-slug>`." Then `coga mark
done`.
