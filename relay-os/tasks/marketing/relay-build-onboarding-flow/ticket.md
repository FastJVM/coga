---
title: Relay build onboarding flow
status: active
mode: interactive
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
step: 1 (design)
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
- Final deliverable is always a launchable ticket batch — the generate step
  rides the `relay ticket` creation primitive (see
  `marketing/relay-ticket-creates`). The spec/vision doc is the durable context
  the batch is generated from.
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
