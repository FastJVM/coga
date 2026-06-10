---
title: maybe-remove-ticket-diagnostic
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
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

Decision made: remove the `eval/ticket-diagnostic` skill. I tested it and haven't been using it.

Remove both copies — the live `relay-os/skills/eval/ticket-diagnostic/` and the packaged `src/relay/resources/templates/relay-os/bootstrap/skills/eval/ticket-diagnostic/` — plus any references to it in contexts/docs.

## Context

- The skill was added by PR [#163](https://github.com/FastJVM/relay/pull/163) (`feat/eval-ticket-diagnostic`) as an opt-in, human-invoked cold-read diagnostic; it was never wired into any workflow, so removal should not break workflow steps.
