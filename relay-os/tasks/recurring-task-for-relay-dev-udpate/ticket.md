---
title: 'Add recurring task: daily relay dev-update Slack digest'
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Add a recurring task that posts a short daily digest of commits merged to
`main` to Slack — a low-effort daily pulse on what is shipping in Relay.

Resolved directly in the bootstrap session rather than as a tracked
implementation ticket: the deliverable is one markdown template, so it was
written in place. See the blackboard for what was created. This draft task
can be deleted (`relay delete recurring-task-for-relay-dev-udpate`).

## Context

The recurring system scaffolds a task per schedule period from templates
under `relay-os/recurring/`. The new template is repo-specific (owner `nick`,
digests this repo), so it lives only in the live repo, not as a packaged
`relay init` seed — consistent with how `dream.md` describes repo-specific
recurring maintenance.
