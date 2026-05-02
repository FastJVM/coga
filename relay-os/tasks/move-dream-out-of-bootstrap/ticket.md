---
title: Move Dream out of bootstrap
status: active
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
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
step: 1 (implement)
---

## Description

Move Dream from the bootstrap namespace into the project-owned recurring
maintenance model.

Bootstrap shims are stateless launch helpers. Dream is not a bootstrap helper;
it is ongoing project maintenance for one repo-level `relay-os/`. The current
`bootstrap/dream` skill should become a normal Dream workflow and skill tree
that each project can carry, customize, and run on a recurring schedule.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

Current files to inspect:

- `relay-os/skills/bootstrap/dream/SKILL.md`
- `relay-os/skills/bootstrap/dream/scan.py`
- `src/relay/resources/workflows/bootstrap/dream-run.md`
- `src/relay/resources/recurring/weekly-dream.md`
- `src/relay/resources/templates/relay-os/`

## Acceptance criteria

- [ ] Project Dream lives under `relay-os/skills/dream/`, not
      `relay-os/skills/bootstrap/dream/`.
- [ ] The recurring workflow is named as Dream, not bootstrap.
- [ ] `relay init --update` installs or refreshes the new Dream resources.
- [ ] Existing docs, templates, and examples no longer teach Dream as a
      bootstrap shim.
- [ ] Focused tests or fixture checks cover the resource move.
