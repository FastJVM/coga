---
title: Relay build onboarding flow
status: draft
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

- Entry mechanic (settled): `relay init` stays pure — it only creates the repo
  files — and drops this ticket as `active`, then points the user at `relay
  build` — the renamed
  `relay setup` command (see companion ticket), which captures the user's name
  and launches this ticket. Name capture stays in the command, so no prompt is
  added to `relay init`.
- One linear workflow handles both repo states: the scan step no-ops on an
  empty repo (output is intent-only starter tickets) and is load-bearing on a
  filled one. Shape: ask → agent-led chat → scan → spec (with in-chat sign-off)
  → generate ticket batch.
- Spec sign-off is in-chat, NOT a separate workflow step. The agent presents the
  drafted spec, takes the owner's confirmation in the same step, then proceeds
  straight to generating tickets. Found while prototyping (2026-06-16): a
  standalone human `review-spec` step is redundant — the agent had already
  gotten verbal sign-off when it presented the spec, then bumped to the formal
  step anyway, producing a double sign-off and a confusing stop right before
  tickets. An interactive step already pauses for the human in-chat, so the
  extra gate buys nothing.
- Read `relay show marketing/init-questions` before designing — it holds the
  dry-run eval and the load-bearing finding (answers-only recovered ~7/20
  facts; the scan recovered all 20). Even with one scripted question, keep the
  scan load-bearing or the empty-repo starter is fact-thin. Carry its rules:
  stub-and-ask (never fabricate); repo docs win on facts, answers win on intent.
- Final deliverable is always a launchable ticket batch — the generate step
  rides the `relay ticket` creation primitive (see
  `marketing/relay-ticket-creates`). The spec/vision doc is the durable context
  the batch is generated from.
- Batch ending (owner decision 2026-06-16, supersedes validate finding #4's
  "one launchable anchor"; batch size ~5 still stands): create the batch as
  **drafts** with **no pre-chosen anchor** — which to launch first is the
  human's call, not the agent's. End in-chat (no separate approval workflow
  step — same reasoning as the spec sign-off collapse): present a numbered
  "next steps" list, get the human's approval, then hand over the
  `relay launch <slug>` command for whichever they pick.
- Parent: `marketing/onboarding-plan` (this realizes its "fast to launchable
  work" goal and updates its "no interview" stance to "one scripted question +
  agent-led chat"). Companion: `marketing/remove-relay-setup-command` (the
  `relay build` command + retiring `relay setup`; slug to be renamed to
  `relay-build-command`).
- Validation: `marketing/validate-relay-build-onboarding` exercises this across
  empty / filled / ±CLAUDE.md repos.
