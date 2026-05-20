---
title: Add dev test run skill
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
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

Add a generic dev workflow skill for running a repo's declared tests and
summarizing exact results.

This should be imported/adapted from a good existing test-runner skill where
possible. Candidate prior art includes `sanity-labs/test` for failure reporting
and `ingpoc/SKILLS/testing` for code-verified evidence.

## Context

This is the replacement for the cancelled unit-test Dream worker. Test execution
belongs in dev workflows. Dream may later suggest missing test contracts, but it
does not own normal dev test execution.

## Acceptance criteria

- [ ] A generic `dev/test-run` or equivalent skill exists.
- [ ] The skill reads the repo's established testing contract; it does not
      invent commands.
- [ ] It can run unit tests and, when configured, narrower affected-test
      commands.
- [ ] It reports exact command, exit code, pass/fail/skip counts when available,
      failing test names, and relevant failure snippets.
- [ ] It classifies failures as known/new/unknown only when evidence exists.
- [ ] Passing runs are reported concisely and do not create noisy PRs.
- [ ] The skill is generic: no hard-coded pytest, pnpm, Maven, Gradle, Cargo,
      or shell-script convention unless that is the repo's declared contract.
