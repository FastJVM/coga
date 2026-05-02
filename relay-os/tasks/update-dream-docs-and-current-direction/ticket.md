---
title: Update docs for per-project Dream
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

Make the per-project Dream model canonical in docs and contexts.

The current material still frames Dream partly as `bootstrap/dream`. After the
implementation tickets land, docs should describe Dream as recurring
project-owned maintenance, with bootstrap reserved for stateless launch helpers.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

Likely files:

- `docs/spec.md`
- `docs/spec-audit.md`
- `README.md`
- `relay-os/contexts/relay/architecture/SKILL.md`
- `relay-os/contexts/relay/cli/SKILL.md`
- `relay-os/contexts/relay/current-direction/SKILL.md`
- `relay-os/skills/bootstrap/dream/SKILL.md` if it still exists

## Acceptance criteria

- [ ] Docs explain that Dream is per repo/project, not global.
- [ ] Docs no longer teach Dream as a bootstrap shim.
- [ ] Docs distinguish Dream orchestration from independent workers.
- [ ] Done-ticket cleanup is documented as retro-first, delete-second.
- [ ] Current-direction reflects the new model and names the first enabled
      workers.
