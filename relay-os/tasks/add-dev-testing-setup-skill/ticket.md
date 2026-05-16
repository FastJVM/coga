---
title: Add dev testing setup skill
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
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    assignee: owner
step: 1 (implement)
---

## Description

Add a generic dev testing setup skill for project start or repo onboarding.

The setup skill should establish how a dev repo declares and documents its test
harness: unit-test command, broader validation commands, fixture/data rules,
known-failure policy, and CI parity. It should be generic across languages and
frameworks.

## Context

This is the "set up the test harness at project start" part of the testing
skill family. It should be informed by imported testing skills where useful,
but not hard-code Relay's own Python test command.

## Acceptance criteria

- [ ] A generic `dev/testing-setup` or equivalent skill exists.
- [ ] It discovers existing project test conventions before proposing new ones.
- [ ] It documents where the repo's unit-test and validation commands live.
- [ ] It defines known-failure/baseline policy without encouraging agents to
      hide new failures.
- [ ] It covers fixture/data setup and external-service boundaries.
- [ ] It produces a project-local testing contract that `dev/test-run` can read.
