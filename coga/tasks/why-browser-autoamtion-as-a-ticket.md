---
slug: why-browser-autoamtion-as-a-ticket
title: why browser autoamtion as a ticket
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: autonomy/assist-only
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-coga
    skills: []
    assignee: agent
secrets: null
script: null
step: 2 (human-owns-and-finishes)
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

## Investigation

- Current behavior is direct, not inferred: `copy_fresh_templates()` copies the
  packaged tree except `bootstrap/`; `_do_init()` then calls
  `_prune_onboarding_tickets()` only for a filled repo, and that function's
  allowlist contains only `coga-build`. The browser ticket therefore survives
  both empty- and filled-repo init. Existing tests explicitly assert this.
- The history records conflicting deliberate choices, rather than a simple
  forgotten prune-list update. Commit `b58b242b` (2026-05-29) added the browser
  workflow, contexts, skills, and ticket together so they would "ship as
  framework defaults." Commit `d73e3978` (2026-06-10) then deleted the live
  dogfood ticket as a "speculative launcher; methodology lives in browser/
  workflows, contexts, and skills," but left the packaged template behind.
  Commit `e455b4c3` (2026-06-18) later introduced the empty/filled onboarding
  gate, changed the packaged browser ticket's owner from `zach` to the
  stampable `new-user`, and added tests saying the browser draft "ships on
  every repo (not gated)." The near-empty task-list premise was therefore not
  an invariant at that time, even though the earlier live-ticket deletion had
  already articulated the cleaner primitive boundary.
- The historical intent does not make the present representation a good fit.
  The file describes a reusable entry point, not work the installing user
  chose. Init nevertheless materializes it as a real `draft`, attributes it to
  that user, and exposes it in normal task status. The packaged `coga/log.md`
  also carries its original `2026-05-28 ... [human:zach] created` audit line,
  making the new repo look as though it inherited someone else's work history.
- Removing only this seeded ticket does not remove the browser battery:
  `browser/build-automation`, the `browser/*` contexts, and the package-backed
  `browser/playwright` skill resolve independently of the task file.

## Recommendation

**Remove `src/coga/resources/templates/coga/tasks/browser-automation.md` from
the init payload; do not merely add it to the filled-repo prune list.** Keep the
browser workflow, contexts, and Playwright skill available as the reusable
battery. If a browser demo is useful, put a *concrete example task* under
`example/coga/tasks/` rather than moving this generic launcher unchanged. A
short docs/orientation pointer can preserve discovery without manufacturing
work in every user's task list.

Why: a ticket should assert real, chosen work. This file instead advertises a
capability and waits for the user to supply the actual task. Materializing it
as a normal draft, stamping the installer as its owner, and carrying the
original author's audit line blur that boundary. The June 10 live-copy
deletion already captured the right separation: methodology belongs in the
browser battery; a concrete automation gets its own ticket when requested.

### Options weighed

1. **Remove from shipped tasks; use `example/` for a concrete demo
   (recommended).** Keeps every installed task list truthful and leaves all
   browser capability available. Cost: lower zero-click discoverability;
   mitigate with a small docs/orientation mention if that proves important.
2. **Add it to `_ONBOARDING_TICKET_DIRS`.** Minimal code change and cleans
   filled repos, but leaves an unsolicited feature draft in every empty repo
   and misclassifies a browser launcher as onboarding. It preserves the
   semantic problem behind another filename exception.
3. **Leave it as-is.** Best immediate discoverability and faithful to the
   explicit June 18 test contract. Cost: status/audit pollution and a generic
   capability masquerading as user-owned work; not worth it.
4. **Make the whole browser battery opt-in.** Cleans the surface but removes
   useful reusable capability and adds installation/configuration machinery.
   This is broader than the problem and conflicts with the small-surface
   posture.

A package-backed stateless bootstrap launcher is a possible future UX, but it
is not a simple destination move: bootstrap launches are single-shot while
the current router spans a four-step workflow. Do not fold that redesign into
the cleanup follow-up.

### Follow-up scope if accepted

- Delete the packaged browser task; the live `coga/tasks/` copy is already
  absent, so this restores rather than breaks live/template consistency.
- Remove the stale browser-automation line from the packaged `coga/log.md`.
- Replace init tests that assert universal browser-ticket seeding with
  assertions that empty and filled installs contain no browser draft.
- Optionally add a concrete browser example plus one discoverability pointer.
- Leave the browser workflow, contexts, and skill untouched.

No code change is part of this decision ticket.
