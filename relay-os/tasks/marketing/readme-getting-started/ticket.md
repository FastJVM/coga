---
title: README Getting Started section
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

Write a clear "Getting Started" section in the repo README — the shortest path
from nothing to a running agent: install the CLI, create a project, `relay init
--user`, `relay build`, `relay launch`. **Win:** a newcomer follows the section
start-to-finish and reaches a launchable ticket.

## Context

- The flow to teach (fresh-directory path): install the CLI (`git clone` the
  source + `pip install -e .`), then `mkdir` a new dir + `git init`, `relay init
  --user <name>`, `relay build` (one scripted question + an agent-led chat that
  ends in a first batch of draft tickets), `relay launch <slug>`.
- Ground every command description in real behavior (`relay --help`, the
  `relay/architecture` context) — don't invent.
- Enablers (shipped): `relay build` replacing the relay-setup interview, the
  `relay setup` → `relay build` rename, `relay init --user`, init auto-seeding
  the onboarding ticket and surfacing `relay build`, and `relay launch`
  activating a draft before running it. Still open: `relay ticket`
  create-and-build (`marketing/relay-ticket-creates`); and `relay init` does
  **not** `git init` an empty dir (a silent skip) — document the `git init` step
  until a follow-up fixes it.
