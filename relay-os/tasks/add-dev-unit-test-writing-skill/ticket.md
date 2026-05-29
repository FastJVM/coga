---
title: Add dev unit-test writing skill
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

Add a generic dev skill for writing and updating good unit tests.

This should import/adapt existing prior art where useful, especially skills that
emphasize project-conformant tests and low-scaffolding deterministic coverage.
Candidate prior art includes `ArcaneArts/update-unit-tests` and similar
project-conformant unit-test skills.

## Context

This is distinct from `dev/test-run`. `dev/test-run` executes the repo's
declared command. This skill helps create or update tests while preserving the
project's existing style.

## Acceptance criteria

- [ ] A generic `dev/unit-test-writing` or equivalent skill exists.
- [ ] It learns from nearby/existing tests before writing new tests.
- [ ] It favors deterministic unit-level coverage over large integration
      scaffolding.
- [ ] It covers success, boundary/edge, and failure/error behavior when
      applicable.
- [ ] It avoids overspecifying implementation details and avoids brittle
      snapshot-like assertions unless already standard in the repo.
- [ ] It explains when to stop and ask because behavior intent or test harness
      setup is ambiguous.
- [ ] It uses `dev/test-run` or the repo's testing contract to verify the tests
      it writes.
