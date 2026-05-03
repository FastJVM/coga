---
title: Add dev unit-test Dream worker template
status: done
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts:
  - relay/codebase
  - relay/current-direction
  - relay/project-stage
  - dev/code
workflow:
  name: code/with-review
  steps:
    - name: implement
      skill: code/implement-and-pr
    - name: review
---

## Description

Add a project-specific Dream worker template for running unit tests in a code
repo.

This should not hard-code Relay's Python test command as the universal answer.
The worker should define a convention for each repo to declare its test command,
then run that command during Dream and summarize exact failures.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

Example for this repo might be `python -m pytest`, but the useful output is the
template/convention a dev project can customize.

## Acceptance criteria

- [ ] A `dream/tasks/dev/unit-tests` worker template exists.
- [ ] The worker documents where the project-specific test command is declared.
- [ ] Test failures are summarized with exact command, failing test names, and
      whether the failure is new or known when that evidence exists.
- [ ] Passing runs are reported concisely and do not open noisy PRs.
- [ ] Missing test-command configuration fails loud with an actionable message.
