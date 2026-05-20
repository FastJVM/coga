---
title: Track retro completion for Dream
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement-and-pr
  - name: review
---

## Description

Define and implement the idempotency marker for done-ticket retros.

Dream must not retro the same done ticket repeatedly. The marker should be
legible, git-backed, and resilient after the task directory is deleted by the
retro PR.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

Possible approaches:

- Branch naming convention such as `retro/<task-slug>`.
- PR body marker with the source task slug and commit.
- Git history search for a deleted task path.
- A small metadata file, if that does not create more state than it removes.

## Acceptance criteria

- [ ] The chosen marker is documented in the Dream worker contract.
- [ ] Dream can identify done tickets with no completed retro.
- [ ] Dream can identify tickets whose retro PR is open and avoid duplicate PRs.
- [ ] Dream can identify tickets whose retro already merged, even if the task
      directory is gone.
- [ ] The marker does not require a database, daemon, or hidden local cache.
