---
title: relay-setup
status: active
mode: interactive
owner: new-user
human: new-user
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: init/setup
  steps:
  - name: interview
    skills: []
    assignee: agent
  - name: scan-and-generate
    skills: []
    assignee: agent
  - name: resolve-open-questions
    skills: []
    assignee: agent
  - name: review-and-sign-off
    skills: []
    assignee: human
  - name: apply-review
    skills: []
    assignee: agent
step: 1 (interview)
---

## Description

Interview the owner, then turn the answers plus a scan of this repo into
durable relay-os artifacts — contexts, rules, workflows, recurring tasks,
possibly skills — so future agents start already knowing the project
instead of starting from zero. The interview is the first workflow step:
launching this ticket starts it. Generated files are drafts for the
owner's review; nothing is final without sign-off.

## Context

Empty until the `interview` step runs at first launch — the agent records
the owner's answers to the four setup questions here verbatim.
