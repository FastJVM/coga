---
slug: packaged-repos-ship-recurring-templates-without-th
title: Packaged repos ship recurring templates without the coga recurring context
status: draft
owner: nicktoper
human: nicktoper
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`coga/contexts/coga/recurring/SKILL.md` is ~35 KB carrying the recurring system's whole contract:
template directory shape, `schedule:` / `workflow:` / `state_keys:` frontmatter, the control-branch
and `owner` gates, the serviced-period ledger in `coga/log.md`, the `ticket.py` deduction rule, and
promotion rules. It is **not** in the packaged bootstrap contexts
(`src/coga/resources/templates/coga/bootstrap/contexts/coga/`), while the recurring *templates*
themselves are packaged.

So a fresh `coga init` repo gets working recurring templates and none of the knowledge explaining
them. Decide whether to package the context, or to split a smaller operator-facing subset.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-08), classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
