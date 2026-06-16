---
title: onboarding-plan
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- marketing/positioning
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
  - name: report-to-relay
    skills: []
    assignee: agent
step: 1 (agent-produces)
---

## Description

Define Relay's onboarding plan: the shortest path that gets a new user to
real value within ~30 seconds. Identify the exact commands to guide someone
through — `git clone` → `relay init` → `relay build` → `relay launch <ticket>`
— and write a short onboarding document that walks them through it. Win
condition: `relay build` leaves the user with a first batch of tickets they can
`relay launch` immediately.

## Context

- The flow to teach: clone the repo, run `relay init` (downloads relay-os);
  at the end of init, run `relay build` — one scripted question ("what do you
  want to build?") plus an agent-led chat (and a repo scan on a filled repo)
  that ends in a first batch of draft tickets — then `relay launch <slug>` to
  start one. Detailed design: `marketing/relay-build-onboarding-flow`.
- Deliverables: (1) the recommended onboarding command sequence, (2) a short
  onboarding document describing it.
- Document the *target* flow above; flag any step the enablers below haven't
  made live yet. Ground command descriptions in real behavior (read
  `relay/architecture` and `relay --help` at work time) — don't invent.
- Enablers, tracked as separate follow-up tickets (out of scope here):
  replace the `init/setup` relay-setup interview with `relay build` — keep one
  scripted question + an agent-led chat, not the old 5-step interview
  (`marketing/relay-build-onboarding-flow`, and the command rename in
  `marketing/remove-relay-setup-command`); make `relay ticket` create *and*
  build the ticket (`marketing/relay-ticket-creates`); make `relay launch` mark
  a drafted ticket active before running it; auto-draft the onboarding ticket on
  `relay init` and surface the `relay build` recommendation when init finishes.
