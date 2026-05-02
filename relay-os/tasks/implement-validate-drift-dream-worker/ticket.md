---
title: Implement validate-drift Dream worker
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

Turn Relay validation into an independent Dream worker.

The worker runs `relay validate --json`, classifies issues, and produces
concrete remediation proposals or small PRs according to severity and safety.
This keeps deterministic repo checks inside Dream without making the whole
Dream run one validation script.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

Current related code and docs:

- `src/relay/validate.py`
- `relay-os/skills/bootstrap/dream/scan.py`
- `relay-os/skills/bootstrap/dream/SKILL.md`
- `docs/spec.md` validation and dream/drift sections

## Acceptance criteria

- [ ] A `dream/tasks/validate-drift` worker exists.
- [ ] It runs the same deterministic validation surface as
      `relay validate --json`.
- [ ] It classifies each issue into direct fix, PR proposal, or human-needed.
- [ ] Stale-lock handling follows a conservative documented rule.
- [ ] The worker reports a concise result into the Dream run blackboard.
- [ ] Existing validation tests still pass or are updated for the new shape.
