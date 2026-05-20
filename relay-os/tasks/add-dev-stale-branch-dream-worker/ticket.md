---
title: Add dev stale-branch Dream worker template
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/principles
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
    - code/implement-and-pr
  - name: review
---

## Description

Add a project-specific Dream worker template for stale branch cleanup in a code
repo.

Branch deletion is destructive enough that the first version should propose
cleanup with evidence, not silently delete branches. Direct deletion can be a
later tightening only for branches proven merged under a conservative rule.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

This worker should handle local branches, remote-tracking branches, and old
topic branches separately. Each category has different risk.

## Acceptance criteria

- [ ] A `dream/tasks/dev/stale-branches` worker template exists.
- [ ] It identifies merged local branches with the exact git evidence.
- [ ] It identifies stale remote-tracking branches separately from local
      branches.
- [ ] It avoids touching protected branches such as `main`.
- [ ] It outputs a proposal or PR with commands/evidence before deletion.
- [ ] It documents when direct deletion is allowed, if any direct deletion is
      implemented.
