---
title: Validate relay build onboarding
status: done
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: build/dry-run
  steps:
  - name: prepare-fixtures
    skills: []
    assignee: agent
  - name: dry-run-and-score
    skills: []
    assignee: agent
  - name: synthesize
    skills: []
    assignee: agent
---

## Description

Dry-run the `relay build` onboarding flow *before* it is built, to validate the
one-question premise and de-risk the design — mirroring the pre-implementation
dry run that validated the old interview (`marketing/init-questions`). The agent
role-plays `relay build` across three throwaway fixture repos (empty / filled /
filled-with-CLAUDE.md), actually creates the starter tickets in each so they can
be launched for real, and the human scores each run. Findings feed the
`marketing/relay-build-onboarding-flow` design — so this runs **first**.

## Context

- How it runs: the `build/dry-run` workflow drives it
  (`relay-os/workflows/build/dry-run.md`) — prepare-fixtures → dry-run-and-score
  → synthesize. Activate and launch it (`relay mark active` then `relay launch`)
  and the agent walks you through fixture setup, the three dry runs, and scoring.
- High fidelity: tickets are created for real inside each fixture repo (each
  gets `relay init`'d), so you can `relay launch` one or two and feel the flow.
  The fixtures are throwaway — delete them after.
- The rubric is grounded in the `init-questions` scorecard (the 7/20-vs-20/20
  recall measure) so the numbers are comparable to the prior eval.
- Sequence: this dry run → `relay-build-onboarding-flow` design → the `relay
  build` command (`remove-relay-setup-command`).
