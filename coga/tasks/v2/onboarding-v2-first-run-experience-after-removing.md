---
slug: v2/onboarding-v2-first-run-experience-after-removing
title: Onboarding v2 — first-run experience after removing coga build
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

Design a real first-run onboarding experience for a fresh `coga init` repo, now
that `coga build` (the packaged `coga-build` onboarding ticket) and
`coga project` are being removed as never-used entry points
(see `remove-coga-build-and-project`). After that removal, `coga chat`
(orient) is the single conversational door; the interim story is just a
pointer from `coga init` output and docs to `coga chat`.

This ticket is deliberate concept-capture: the shape isn't settled, so it
stays a workflow-less draft until we decide what onboarding v2 actually is.

## Context

Open questions to settle before this gets a workflow:

- Should onboarding live inside `bootstrap/orient` (chat detects an empty
  repo and guides setup), or be a distinct guided flow?
- What must a first session produce — vision doc, first tickets, agent
  config, secrets setup?
- The removed `coga-build` ticket and `build` workflow are in git history as
  reference for what v1 tried to do.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
