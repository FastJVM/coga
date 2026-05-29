---
title: Add bootstrap skill for importing external skills
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/current-direction
- relay/project-stage
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Add a bootstrap/process skill that explains how Relay projects import external
Agent Skills instead of writing every reusable playbook from scratch.

The skill should help agents decide when to import an existing skill, when to
adapt one, and when to write a local skill. It should make provenance explicit
so future humans can see what was imported and what was changed locally.

## Context

This came out of `add-dev-unit-test-dream-worker`, where the useful design
became "import/adapt good generic testing skills" rather than inventing a
Dream-specific worker.

Candidate source examples found during design:

- `sanity-labs/test` - test runner shape with failure reporting
- `ingpoc/SKILLS/testing` - code-verified testing evidence
- `ArcaneArts/update-unit-tests` - low-scaffolding unit-test update workflow

## Acceptance criteria

- [ ] A bootstrap/import skill exists in the Relay skill tree.
- [ ] It explains when to import, adapt, or write a new skill.
- [ ] It requires provenance fields or a clear provenance section: source URL,
      upstream repo, import date, local changes, and reason for adaptation.
- [ ] It defines where imported/adapted skills should live in `relay-os/skills/`.
- [ ] It says not to blindly import broad skills that add irrelevant workflow
      or hard-coded commands.
- [ ] It includes a short example import decision for a dev testing skill.
