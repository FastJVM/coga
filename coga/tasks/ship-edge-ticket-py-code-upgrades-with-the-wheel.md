---
title: Ship edge ticket.py code upgrades with the wheel
status: draft
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
---

## Description

Coga ships code that is not in core, such as a recurring template's `ticket.py`, as packaged template files. `coga init` copies them into the repo. After that, `pip install -U coga` updates `src/coga/` but leaves every existing repo running its old copy of the edge code. The only way the new copy arrives is a template sync, if one happens at all.

PR 880 (phone-home telemetry) turns this into a real problem: following the microkernel rule, it moves roughly 340 lines of telemetry logic out of `src/coga/telemetry.py` and into `coga/recurring/phone-home/ticket.py`. A fix to that code, or to its closed payload, would then never reach repos initialized earlier.

Owner direction (2026-09-23, in chat): "upgrade: needs to be written in a ticket, we'll fix it and move it back into the wheel."

### Goal
Edge ticket code that Coga ships must upgrade together with the wheel, without breaking the microkernel rule (core never imports from a ticket or skill directory) or the hackable principle (a repo can still see and change its copy).

### Questions for design
- Should the packaged file be the source of truth, with the repo copy refreshed on upgrade? Or should the repo's `ticket.py` be a thin shim that runs code packaged in the wheel outside `coga.*` core?
- How are local edits detected and kept, instead of being silently overwritten?
- Which existing mechanism takes this on: `coga init` re-run, `upstream-coga`, skill-update, or something new?
- Once this is fixed, move the phone-home telemetry code back into the wheel under the chosen shape, and update `coga/telemetry` and `docs/telemetry.md` to match.

### Related
- PR 880 / `marketing/add-telemetry`
- `recurring-sweep-wedges-on-the-ticket-py-it-copies`
- The gigantic-refactor ticket for recurring recipes (the other recipes will hit the same issue)

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
