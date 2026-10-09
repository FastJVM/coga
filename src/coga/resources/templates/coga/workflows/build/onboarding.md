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

Before writing the vision, resolve **`<contexts-dir>`** from `coga.toml`: use
the checkout-root-relative `[layout] contexts` directory when the key is set,
or `coga/contexts/` when it is unset. Do not assume the default path.

On sign-off:

- Write the agreed vision to **`<contexts-dir>/product/vision/SKILL.md`** in
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

Create each ticket as a **draft, non-interactively** — do not launch a
per-ticket authoring interview. Every draft must carry an explicit workflow so
the handoff really is launchable:

- implementation work: `coga create "<title>" --workflow
  code/design-then-implement` (the ticket is intentionally thin, so its first
  step turns the what+why into a reviewed spec);
- decide/evaluate work: `coga create "<title>" --workflow draft-for-human`
  (the agent prepares the decision material and the human owns the judgment).

After each non-interactive create, add `product/vision` to `contexts:` and write
its thin what+why body. Do not leave any starter ticket with `workflow: null`:
such a draft cannot be activated or launched.

End in chat (no separate approval step): present the flat list and get the
user's approval. Do **not** show a launch command yet — a starter ticket is
launchable only once its vision context is on the published branch, or a fresh
clone gets tickets whose `product/vision` is missing.

After approval, publish the vision and the batch explicitly and confirm it
landed:

```sh
coga run publish-state --message "Publish build vision and starter tickets" \
  <contexts-dir>/product/vision/SKILL.md <each starter ticket file>
```

Name every file: the vision `SKILL.md` and each ticket path `coga create`
printed. The recipe runs the same publication as Coga's end-of-command sweep,
but exits 0 only when every named file is confirmed on the control branch.

- **Exit 0:** hand over the generic launch command — e.g. "Here's your starter
  batch — launch any one with `coga launch <ticket-slug>`." Then `coga bump`.
  (If it reports `[git].enabled = false`, there is no published branch: say
  the batch is launchable from this checkout only, then hand over and bump.)
- **Non-zero exit:** the handoff is unfinished. Do **not** present launch
  commands as ready and do **not** `coga bump`; the files stay on disk as
  written. Tell the user in chat that the handoff is unfinished, quote the
  failure the recipe printed, and say how to retry: fix the cause (for
  example a rejected or unreachable push), then rerun the same
  `coga run publish-state` command, or rerun `coga build` to resume this
  step. Record the same — failure, files left on disk, retry command — on
  this ticket's blackboard under `## Unfinished handoff` (the recipe also
  appends its own `## Recipe Failure` section there). Stay in the chat so the
  user can fix it and you can retry; only an exit 0 lets you hand over and
  bump.
