---
slug: why-browser-autoamtion-as-a-ticket
title: why browser autoamtion as a ticket
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: autonomy/assist-only
secrets: null
script: null
---

## Description

Investigate why a `browser-automation` ticket ships into every fresh Coga
install's task list, decide whether that's the right place, and recommend
where it should actually live. Produce a short written recommendation with the
options laid out and a clear recommended option; the human makes the final
call on the destination. This ticket ends at the recommendation + decision —
if a code change is warranted, it becomes a follow-up.

## Context

A fresh `coga init` copies the whole `src/coga/resources/templates/coga/` tree
into the target repo. Two tickets are seeded into `tasks/` this way:

- `coga-build` — the onboarding/bootstrap interview ticket. On a *filled* repo
  this is pruned by `_prune_onboarding_tickets` (see
  `src/coga/commands/init.py:185`, `_ONBOARDING_TICKET_DIRS`), on the reasoning
  that "a real project doesn't want the bootstrap interview seeded for it."
- `browser-automation`
  (`src/coga/resources/templates/coga/tasks/browser-automation.md`) — a
  plug-and-play "turn a described browser task into a Playwright automation"
  entry point, wired to the `browser/build-automation` workflow and the
  `browser/api-first` context (its frontmatter `skills:` is `[]`; the
  `browser/playwright` skill is referenced only in the ticket prose, reached
  via the workflow, not wired on the ticket).

The asymmetry to investigate: `browser-automation` is **not** in the prune
list, so unlike `coga-build` it lands in every init'd repo (including filled
real projects) as a live `draft` ticket and stays. It reads as a feature demo
seeded into the user's own task list — arguably the wrong place. A new
install's task list should probably be near-empty, not pre-loaded with a
browser-automation feature ticket.

Before inferring the asymmetry is an oversight, check intent: `git log` /
`git blame` both `browser-automation.md` and the `_ONBOARDING_TICKET_DIRS`
prune list to see who added them and whether the difference was deliberate.
The "near-empty task list is the intended new-install state" premise is itself
an assumption — resolve it from history, not by inference.

Options to weigh (destination decided during the ticket, not pre-committed):
add it to the init prune list; move it to `example/coga/` as a demo fixture;
make the whole browser battery opt-in; or **leave it as-is with a
justification** — this last one is a genuinely acceptable outcome, not a
strawman, if history shows the seeding is intentional. The browser
workflow/skills/contexts themselves are batteries and are not in scope — this
is only about the seeded *ticket*. Confirm the actual install behavior by
reading `init.py` rather than assuming; the browser battery (workflow,
`browser/*` contexts, `browser/playwright` skill) should stay available even
if the seeded ticket moves or is pruned.

Follow-up note for whoever implements any move/prune: the destination change
touches the *packaged* template
(`src/coga/resources/templates/coga/tasks/browser-automation.md`), which is
what init copies; per CLAUDE.md the live `coga/tasks/` copy must stay in sync,
so a follow-up must not edit only one copy.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
