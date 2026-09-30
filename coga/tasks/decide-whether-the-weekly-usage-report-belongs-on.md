---
title: Decide whether the weekly usage report belongs on coga-important
status: in_progress
owner: nicktoper
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
step: 1 (implement)
agent: claude
launch_generation: pending:47cac454-51c3-4df2-87dd-e73a80f95810
---

## Description

Filed by Dream 2026-W40, Phase 6 (shard ks-19, class stale, target `docs/contexts/coga/important/SKILL.md`). `coga/important` says the important destination is only for notifications that need a human to act ("Nothing else goes there"). This repo's local recurring template `coga/recurring/usage-report` (`ticket.py` ~line 30, `post(cfg, text, important=True, fatal=False)`; its `ticket.md` step 3) posts a weekly token-usage FYI there, a routing the owner chose explicitly in done ticket `agent-usage-report`. Contract and repo disagree; the owner decides which yields: move the usage report to the flow webhook, or record in `coga/important` (and its packaged twin) that a repo may deliberately route a low-volume periodic report there and why. State also whether repo-local templates are in scope for the `coga/notifications/producers` inventory.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
