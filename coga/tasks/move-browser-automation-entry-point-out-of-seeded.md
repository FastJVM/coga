---
slug: move-browser-automation-entry-point-out-of-seeded
title: Move browser automation entry point out of seeded tasks
status: draft
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Remove the generic seeded `browser-automation` ticket from fresh Coga installs
and preserve the browser automation entry point as reusable capability instead
of standing user-owned work. The accepted product decision is: delete the
packaged task, move the orchestration methodology into a bundled
`browser/build-automation` skill, expose it through a stateless package-backed
bootstrap launcher, and document how users invoke it.

## Context

Source decision: [why-browser-autoamtion-as-a-ticket](coga/tasks/why-browser-autoamtion-as-a-ticket.md).

The decision ticket investigated the history and found that
`src/coga/resources/templates/coga/tasks/browser-automation.md` is copied into
every `coga init` result as a real `draft` ticket. That is no longer the desired
shape: a ticket should assert chosen work, while this file is a capability
launcher waiting for the user to supply the actual browser task.

Implementation scope:

- Delete `src/coga/resources/templates/coga/tasks/browser-automation.md`.
- Remove the stale packaged `browser-automation` audit line from
  `src/coga/resources/templates/coga/log.md`.
- Move the router/orchestration methodology currently encoded in
  `coga/workflows/browser/build-automation.md` and
  `src/coga/resources/templates/coga/workflows/browser/build-automation.md`
  into a bundled `browser/build-automation` skill.
- Keep `browser/playwright` as the separate lower-level execution skill.
- Expose the orchestration skill through a stateless package-backed bootstrap
  launcher so invoking browser automation setup does not create a standing task
  merely by installing Coga.
- Document the launcher and the distinction between the orchestration skill and
  the Playwright runner in user-facing docs.
- Update init/bootstrap/compose tests so empty and filled installs do not
  contain a seeded browser draft, while the browser contexts, workflow support,
  skills, and runtime capability remain available.

Read `AGENTS.md`, `docs/vision.md`, and the relevant `coga/contexts/coga/`
context before changing behavior. When touching shipped templates or contexts,
keep the live `coga/` copy and packaged
`src/coga/resources/templates/coga/` copy in sync unless the difference is
intentional and documented.

<!-- coga:blackboard -->

## Origin

Created from the accepted decision in
`why-browser-autoamtion-as-a-ticket`. Nick chose removal of the seeded ticket
plus a skill/documentation-backed stateless entry point; no further product
destination decision should be needed before implementation.
