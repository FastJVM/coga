---
title: Define Dream worker discovery and dispatch contract
status: active
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: nick
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
workflow:
  name: code/with-review
  steps:
  - name: implement
    skill: code/implement-and-pr
  - name: review
step: 2 (review)
---

## Description

Define how Dream finds and runs independent background maintenance workers.

Dream should be an orchestrator, not a single large cleanup script. Each worker
needs a small, legible contract: what it consumes, what it may change, how it
reports results, and how it avoids repeating work.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

This ticket should answer the generic contract before individual workers grow
their own incompatible conventions.

## Proposed contract surface

- Worker location, for example `relay-os/skills/dream/tasks/<name>/SKILL.md`.
- Worker metadata: name, description, project scope, risk level, and whether it
  can edit directly, must open a PR, or only writes proposals.
- Input selection: how Dream chooses which workers are enabled in a repo.
- Output shape: blackboard summary, PR link, created ticket, or no-op result.
- Idempotency rule: how the worker proves a unit was already handled.
- Safety rule: when the worker must stop and ask for review.

## Acceptance criteria

- [x] `skills/dream/orchestrate` has explicit instructions for discovering
      enabled workers.
- [x] Worker SKILL.md files have a documented metadata/body convention.
- [x] Dream can summarize worker results in one run-level blackboard section.
- [x] Destructive worker behavior requires evidence and review by default.
- [x] The contract is documented somewhere durable enough for project authors
      to add their own `dev/*` workers.
