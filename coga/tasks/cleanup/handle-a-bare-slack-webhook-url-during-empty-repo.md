---
slug: cleanup/handle-a-bare-slack-webhook-url-during-empty-repo
title: Handle a bare SLACK_WEBHOOK_URL during empty-repo init
status: draft
owner: nick
human: nick
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
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`coga init` in an empty git repo crashes with a `ConfigError` traceback when
a bare `SLACK_WEBHOOK_URL` is set in the environment. The existing-project init
path handles the same condition with a friendly tip, so the two paths should
agree.

## Context

**Reproduction** (audit, 2026-09-02, check 2 row h): export
`SLACK_WEBHOOK_URL` (any value), `git init` an empty directory, run
`coga init --user tester`. The empty-repo path — the one that seeds
`coga/tasks/coga-build.md` and prints "Run `coga build`" — raises a
`ConfigError` traceback instead of the tip the existing-project path prints
for the identical environment.

**Scope.** Small: find where the existing-project path handles it and apply
the same handling to the empty-repo path, with a test covering both. Edge
case — it only bites someone who already has that variable exported — but a
traceback on the very first command is the worst possible first impression,
and the fix is a few lines.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
