---
slug: v2/document-recurring-template-live-vs-packaged-sync
title: Document recurring template live-vs-packaged sync rule
status: draft
autonomy: interactive
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

Surfaced by Dream W22 Phase 2 knowledge scan (G10).

The recurring template body under `relay-os/recurring/<name>/ticket.md` IS the
run prompt — when a recurring task fires, that body is composed verbatim as
`## Description` for the spawned task. Relay-shipped recurring templates
(`dream`, future ones) have a packaged twin under
`src/relay/resources/templates/relay-os/recurring/<name>/ticket.md` that
`relay init --update` ships to other repos.

The "live + packaged" mirror rule is in `CLAUDE.md`/`AGENTS.md` (general repo
rule) but absent from `relay/recurring` and `relay/codebase`. A new recurring
author won't know to keep the two in sync; `relay init --update` re-introduces
drift across user repos every release.

Draft outline:

- Add a "Gotchas" bullet to `relay-os/contexts/relay/recurring/SKILL.md`:
  Relay-shipped recurring templates have a packaged twin under
  `src/relay/resources/templates/relay-os/recurring/<name>/`; edits to one
  must be mirrored to the other or `relay init --update` re-introduces drift.
- Or document the same in `relay/codebase` alongside other live/packaged
  pairs.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
