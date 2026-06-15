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
through — `git clone` → `relay init` → `relay ticket <slug-title>` →
`relay launch` — and write a short onboarding document that walks them
through it. Win condition: a first ticket is drafted, launched, and doing
work in about a minute.

## Context

- The flow to teach: clone the repo, run `relay init` (downloads relay-os);
  at the end of init, recommend `relay ticket <slug-title>` to draft a first
  ticket, then recommend `relay launch <slug>` to activate it and start work.
- Deliverables: (1) the recommended onboarding command sequence, (2) a short
  onboarding document describing it.
- Document the *target* flow above; flag any step the enablers below haven't
  made live yet. Ground command descriptions in real behavior (read
  `relay/architecture` and `relay --help` at work time) — don't invent.
- Enablers, tracked as separate follow-up tickets (out of scope here):
  retire the `init/setup` relay-setup interview (onboarding shouldn't require
  an interview); make `relay ticket` create *and* build the ticket; make
  `relay launch` mark a drafted ticket active before running it; auto-draft
  onboarding ticket(s) on `relay init` (possibly two) and surface the
  `relay ticket` recommendation when the download finishes.
