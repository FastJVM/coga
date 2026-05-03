---
title: Add imported-skill update check
status: draft
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: nick
contexts:
  - relay/codebase
  - relay/current-direction
  - relay/project-stage
  - dev/code
workflow:
  name: code/with-review
  steps:
    - name: implement
      skill: code/implement
    - name: open-pr
      skill: code/open-pr
    - name: review
      assignee: owner
step: 1 (implement)
---

## Description

Add a maintenance check for imported/adapted skills.

Imported skills are useful only if humans can tell when upstream changed and
whether local adaptations still make sense. This check should inspect imported
skill provenance, compare it with upstream when possible, and report drift with
reviewable evidence.

## Context

This is related to Dream, but it is not the same as running tests. Dream or a
future recurring maintenance workflow can use this check to notice stale
imported skills.

## Acceptance criteria

- [ ] Imported skills have enough recorded provenance for the checker to read.
- [ ] The checker reports upstream version/commit changes when available.
- [ ] The checker distinguishes upstream changes from local adaptations.
- [ ] The checker reports security or supply-chain concerns when the source
      cannot be fetched or provenance is incomplete.
- [ ] The output is proposal-only: it does not auto-rewrite imported skills.
- [ ] There is a focused test or fixture for at least one imported-skill record.
