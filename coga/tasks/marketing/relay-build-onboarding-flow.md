---
slug: marketing/relay-build-onboarding-flow
title: Relay build onboarding flow
status: done
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

`relay build` is Relay's new first-run onboarding. After `relay init`, the user
runs `relay build` and the only scripted question is "What do you want to
build?" An agent-led chat draws out the rest (it interviews better than a fixed
list), then — for a repo that already has code — a scan reads what's there.
Both paths end in the same place: a short spec/vision doc the user agrees to,
and a first batch of draft tickets they can immediately `relay launch`. This
replaces the long 5-step relay-setup interview: "shorten, don't delete" becomes
"one question, agent-led, ending in launchable work."

## Context

- Entry mechanic: `relay init` asks for the user's name (scripted prompt) and
  seeds this ticket as `active` **only when the repo is empty** (see the gate
  below), pointing the user at `relay build`. `relay build` (renamed from `relay
  setup`) launches this ticket; it requires an already-initialized repo and no
  longer runs `relay init` itself (companion: `marketing/relay-build-requires-init`).
  Name capture moves to `relay init` (reversing the earlier "name stays in the
  command" call) so `current_user` is valid for the bootstrap machinery usable
  right after init — see `marketing/relay-init-captures-name`.
- Empty-repo-only (owner decision 2026-06-17): the onboarding supports empty
  repos only and the **scan step is removed**. Shape: ask → agent-led chat →
  spec (with in-chat sign-off) → generate ticket batch.
- Intake budget (owner decision 2026-06-17): one scripted question + at most 2
  follow-ups, and the follow-ups target only *shape-defining* unknowns (what /
  scope — CLI vs web app, is-X-in-scope-for-v1). Detail/decision unknowns (which
  library, which provider, exact formula) are NOT chased in intake — they become
  ticket candidates (usually "decide/evaluate X" tickets), which the agent names
  at spec sign-off so the deferral is visible and the user can pull a genuinely
  shape-defining one back into the chat. Why: first-run value is fast launchable
  tickets + flow, not an exhaustive interview, and sign-off backstops the short
  intake. Keep open-question (decision) tickets a subset of the batch, not the bulk of it.
- Empty/filled gate lives in `relay init`, checked **before it writes any
  files**: a repo is *empty* if it holds nothing but `.git/`, `.DS_Store`, and
  relay's own files — **any** other file makes it *filled*. Empty → seed this
  ticket + next-steps points at `relay build`. Filled → don't seed (so there's
  nothing to launch or bypass) + next-steps coaxes to `relay ticket`. No
  build-time guard needed — the init gate covers the common path.
- Spec sign-off is in-chat, NOT a separate workflow step. The agent presents the
  drafted spec, takes the owner's confirmation in the same step, then proceeds
  straight to generating tickets. Found while prototyping (2026-06-16): a
  standalone human `review-spec` step is redundant — the agent had already
  gotten verbal sign-off when it presented the spec, then bumped to the formal
  step anyway, producing a double sign-off and a confusing stop right before
  tickets. An interactive step already pauses for the human in-chat, so the
  extra gate buys nothing.
- Why drop the scan (owner decision 2026-06-17): `relay show
  marketing/init-questions` found the scan load-bearing on filled repos
  (answers-only ~7/20 facts, scan ~20/20) — so intent-only on a filled repo
  would propose rebuilding features that already exist. The scan is also the one
  unbounded-cost step (a barrel-to-busbar dry run hit ~250k tokens / 3 subagents;
  a large repo could run to ~$100, worst at first run). v1 resolves both by
  removing the scan and restricting to empty repos; the empty/question-only path
  scored 8–9/10 in the dry run, so it stands alone. Filled-repo onboarding
  returns later behind a bounded, opt-in scan with a hard token ceiling
  (deferred). Empty-path rule still carries from init-questions: stub-and-ask,
  never fabricate.
- Final deliverable is always a launchable ticket batch — the generate step needs
  only non-interactive bulk draft creation, which ships today (`create_task`,
  surfaced as `relay create`); it upgrades to the consolidated `relay ticket`
  primitive if/when `marketing/relay-ticket-creates` lands, but does not depend on
  it. The spec/vision doc is the durable context the batch is generated from.
- Batch ending (owner decisions 2026-06-16 / 2026-06-17, supersedes validate
  finding #4's "one launchable anchor" and its "~5" size): create the batch as
  **drafts** with **no pre-chosen anchor** — which to launch first is the human's
  call. **No count cap** — generate as many tickets as the spec genuinely
  supports (build + "decide/evaluate X" tickets), never padding to a number nor
  truncating real work (usually a handful). **No ordering, grouping, or
  recommendation** — which ticket to run first is the human's call, with context
  the agent lacks; present one flat list — don't rank, don't bucket (not even
  "build" vs "decision"), don't suggest a starting point. End in-chat
  (no separate approval step): present a flat list (slug + one-line each, neutral
  order), get the human's approval, then hand over the generic launch command —
  e.g. "Here's your starter batch — launch any one with `relay launch
  <ticket-slug>`."
- Parent: `marketing/onboarding-plan` (this realizes its "fast to launchable
  work" goal and updates its "no interview" stance to "one scripted question +
  agent-led chat"). Companion: `marketing/remove-relay-setup-command` (the
  `relay build` command + retiring `relay setup`; slug to be renamed to
  `relay-build-command`).
- Validation: `marketing/validate-relay-build-onboarding` exercised this across
  empty / filled / ±CLAUDE.md repos; the filled / ±CLAUDE.md legs now inform the
  deferred filled-repo path, and the empty leg is what v1 ships.

## Acceptance Criteria

- A `build/onboarding` workflow exists (superseding `init/setup`) with exactly
  **two agent steps and no scan step**:
  1. `gather-and-spec` (assignee `agent`, runs interactively) — asks the single
     scripted question "What do you want to build?", runs an agent-led chat of
     **at most two follow-ups** that target only shape-defining unknowns, drafts
     a short vision, takes **in-chat sign-off** (no separate review step), writes
     the signed-off vision to a durable context, then bumps.
  2. `generate-batch` (assignee `agent`) — reads the vision context, creates a
     flat batch of **draft** tickets, ends in-chat with the generic launch
     handoff, then `relay mark done`.
- Step 1 produces a short **vision context** at
  `relay-os/contexts/product/vision/SKILL.md` (in the *user's* repo): a few
  sentences — what / who / success + v1 scope shape — with valid `SKILL.md`
  frontmatter, framed as a living starter doc the owner edits as the project
  evolves. Raw intake / working notes stay transient on the blackboard.
- The chat does **not** chase detail/decision unknowns (library, provider,
  formula); those are named at sign-off as deferred and become "decide/evaluate
  X" ticket candidates. The owner may pull a shape-defining one back into chat.
- Every generated ticket is a **draft**, has a thin what+why body, and lists the
  vision context in its `contexts:` frontmatter, so a later `relay launch <slug>`
  is oriented by the product without re-stating it.
- The batch has **no pre-chosen anchor, no count cap, and no ordering, grouping,
  or recommendation** — one flat list (slug + one line each, neutral order). The
  "decide/evaluate X" tickets are a **subset**, not the bulk.
- No `scan-and-generate`, `resolve-open-questions`, `review-and-sign-off`, or
  `apply-review` step survives anywhere in the flow.
- The delivered onboarding ticket template carries the frozen `build/onboarding`
  workflow snapshot (the two steps above) and a thin what+why body.
- Live (`relay-os/workflows/...`) and packaged
  (`src/relay/resources/templates/relay-os/...`) copies are in sync;
  `relay validate` passes (the delivered ticket's workflow snapshot matches the
  workflow file).

## Proposed Shape

Authored files (this ticket owns the **content**; see the coordination note):

- `relay-os/workflows/build/onboarding.md` **+** packaged
  `src/relay/resources/templates/relay-os/workflows/build/onboarding.md` — the
  new two-step workflow, full step prose inline (same shape as `init/setup.md`,
  `skills: []` per step). The `build/` namespace already exists live (alongside
  `build/dry-run.md`); the packaged side gains a new `build/` dir.
- packaged `src/relay/resources/templates/relay-os/tasks/relay-build/ticket.md`
  — the delivered onboarding ticket: thin body + frozen `build/onboarding`
  snapshot. (Delivered ticket is packaged-only; relay-cli doesn't onboard
  itself.)

The vision context is **not** a file in this repo — it is created at runtime in
the user's repo by step 1; the workflow prose specifies its path and shape.

Workflow frontmatter:

```yaml
name: build/onboarding
description: First-run onboarding — one scripted question, an agent-led chat, a signed-off vision, and a flat batch of launchable draft tickets. Empty repos only; no scan.
steps:
  - name: gather-and-spec
    assignee: agent
  - name: generate-batch
    assignee: agent
```

`gather-and-spec` prose covers: assume `current_user` is valid (set by `relay
init` — name capture is a companion ticket, do not re-prompt); ask the one
scripted question; run ≤2 shape-defining follow-ups (draw out intent, don't
interrogate); draft the short vision and present it in the same turn for
sign-off; at sign-off, name the deferred decisions so they're visible; on
sign-off write `contexts/product/vision/SKILL.md` and record raw notes on the
blackboard; `relay bump`.

`generate-batch` prose covers: read the vision context (+ blackboard); generate
as many drafts as the vision genuinely supports (build tickets + a subset of
"decide/evaluate X"), no padding/truncation/cap; each draft thin, `status:
draft`, `contexts: [product/vision]`; no anchor/ordering/grouping; create each as
a bare draft non-interactively (no per-ticket authoring interview) — the
load-bearing capability is non-interactive bulk draft creation, which ships today
via `create_task`; name the command `relay create <slug>` for now, upgrading to
`relay ticket <slug>` if/when `marketing/relay-ticket-creates` consolidates
creation. Build does not block on that ticket — only the printed command name
changes, and the fallback (`relay create`) is the already-sanctioned survivor.
Then present the flat list, get approval, hand over "launch any one with `relay
launch <ticket-slug>`"; `relay mark done`.

Coordination note (resolved at implement): `relay-build-command` claims the
`init/setup`→`build/onboarding` and `relay-setup`→`relay-build` renames. This
ticket authors the new files **additively** (`build/onboarding.md` live +
packaged, and the packaged `relay-build/` delivered ticket) and removes nothing:
deleting the stale `init/setup` + `relay-setup` here would break the still-live
`relay setup` command and the tests that cover it (`tests/test_init.py`,
`tests/test_setup.py`), all of which are out of scope (→ `relay-build-command`).
Removal therefore rides with the command swap, which updates those tests and the
init next-steps text in the same change. Interim consequence until the siblings
land: a fresh `relay init` seeds both onboarding tickets. This ticket's content
is authoritative.

## Out of Scope

- The `relay build` command, CLI registration, `setup.py`→`build.py`, init
  next-steps text, and the latent `launch()` arg-count bug fix →
  `marketing/relay-build-command`.
- `relay init` capturing the name, the empty/filled gate, seeding the onboarding
  ticket, and killing the `new-user` placeholder / stamping the name →
  `marketing/relay-init-captures-name`.
- The `relay ticket` creation primitive (yes/no defer gate; removing `relay
  draft` / `relay create`) → `marketing/relay-ticket-creates` (nick).
- Filled-repo onboarding and the bounded, opt-in scan with a token ceiling →
  deferred to a future ticket.
- Generating durable contexts / rules / recurring artifacts beyond the single
  vision context — the old `init/setup` ambition, deliberately dropped here.
- `tests/test_setup.py` updates → land with the command rename ticket.

<!-- coga:blackboard -->

# Blackboard — relay-build-onboarding-flow (design step)

## Scope map (what this ticket owns vs. companions)

THIS ticket = the onboarding **flow content**:
- The new `build/onboarding` workflow (replaces `init/setup`) — the step prose
  the agent follows: ask → agent-led chat → spec (in-chat sign-off) → generate
  flat ticket batch. **Scan removed.**
- The delivered onboarding ticket template body (`relay-setup`→`relay-build`):
  Description/Context + workflow snapshot shape.
- Both the live (`relay-os/...`) and packaged
  (`src/relay/resources/templates/relay-os/...`) copies.

Companions (NOT this ticket):
- `relay-build-command` — `relay build` command (rename `setup.py`→`build.py`),
  CLI registration, init next-steps text, AND the file *renames* of the
  workflow + ticket template. Carries the latent launch() arg-count bug fix.
- `relay-init-captures-name` — name prompt in `relay init` + stamping name into
  delivered ticket (kills `new-user` placeholder); likely the empty/filled gate
  + seeding too.
- `relay-ticket-creates` (nick) — the `relay ticket` creation primitive the
  generate step rides. Still in design.

## Current-state findings (investigated 2026-06-17)

- Old flow = `relay-os/workflows/init/setup.md`: 5 steps — interview /
  scan-and-generate / resolve-open-questions / review-and-sign-off /
  apply-review. Aims at durable relay-os artifacts (contexts, rules, recurring),
  NOT a launchable ticket batch.
- Delivered ticket = packaged `tasks/relay-setup/ticket.md`, `status: active`,
  `owner/human: new-user` (placeholder), `workflow: init/setup`.
- `relay-os/workflows/build/dry-run.md` is the **validation harness** (role-plays
  the flow in fixtures), NOT the real flow. Its findings feed this design.
- `relay init` today seeds NO ticket — just prints next-steps pointing at
  `relay setup`. No empty/filled gate exists yet.
- `relay setup` (`commands/setup.py`) = init-if-needed + name-capture + launch
  `relay-setup`. Tested in `tests/test_setup.py` (those tests belong to the
  command rename ticket, not this one).
- No test or `relay validate` rule hard-asserts the *content* of the workflow /
  ticket template, so this ticket's content design has light test coupling.
- Generate step "rides `relay ticket`" but that primitive is still being
  designed by nick → dependency to flag, not resolve here.

## Open Questions (for review-design / present human)

1. **Workflow shape.** RESOLVED (zach, 2026-06-17): **2 steps.**
   - Step 1 `gather-and-spec` (agent, interactive): ask scripted question →
     agent-led chat (≤2 shape-defining follow-ups) → draft spec → in-chat
     sign-off → bump.
   - Step 2 `generate-batch` (agent): read the signed-off spec, create the flat
     draft-ticket batch, end in-chat with launch handoff → `relay mark done`.
   Rationale: each agent step is a fresh session (no carryover); the only clean
   session boundary is after the signed-off spec exists as a durable artifact —
   chat and spec can't be split because the spec is drafted from the live chat.
2. **Where the spec/vision doc persists.** RESOLVED (zach, 2026-06-17):
   **a short vision context** at `relay-os/contexts/product/vision/SKILL.md` in
   the user's repo — a few sentences (what / who / success + v1 scope shape),
   framed as a *living starter doc* the owner edits as the project evolves.
   Generated tickets reference it via `contexts: [product/vision]`. The raw
   intake/working notes stay transient on the blackboard; detail/decisions go to
   tickets. Key distinction that settled it: the durable artifact is the
   *distilled vision*, NOT the raw intake transcript — the batch alone gives
   future agents no project-level orientation, and a context is the right home
   for slow-drifting "what is this project" knowledge. Staleness contained by
   keeping it high-level (decisions → "decide/evaluate X" tickets).
3. **File ownership vs. command ticket's rename.** OPEN — for review-design.
   Recommend framing this
   ticket as "own the content wherever the files live" — edit whichever path
   exists (`init/setup`+`relay-setup` if command ticket hasn't landed, else the
   `build/onboarding`+`relay-build` names). Keeps the split clean and
   ordering-robust. Flag for review-design to confirm.
