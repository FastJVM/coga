---
title: Shorten relay-setup interview flow
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

The `relay-setup` ticket that `relay init` auto-creates is a great first-launch
hook — a brand-new user has something to run immediately. But the interview
behind it is too long: a total newcomer won't sit through a multi-question,
multi-step interview just to set up their repo. Propose a lighter flow that
still produces useful starter context blocks — the main payoff of setup —
without the long sit-down. This ticket is the brainstorming/design platform for
that change; the `design` step proposes options before anything ships.

## Context

- What's being changed: the `init/setup` workflow
  (`relay-os/workflows/init/setup.md`) — today a 5-step flow whose `interview`
  step asks several broad questions (repo purpose, tacit knowledge,
  recurring/scheduled work), plus a `resolve-open-questions` round and a human
  review/sign-off. That whole arc is the heavyweight part for a newcomer.
- The auto-created ticket it drives: template at
  `src/relay/resources/templates/relay-os/tasks/relay-setup/ticket.md`. The
  workflow has two synced copies (live + packaged under
  `src/relay/resources/templates/…`).
- Focus: get a newcomer to a few useful starter context blocks with far fewer
  touchpoints — shorten, don't delete. Companion to
  `marketing/remove-relay-setup-command`.

