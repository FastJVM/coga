---
slug: no-durable-runbook-covers-running-coga-headless
title: No durable runbook covers running Coga headless
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

Three separate `v2/` drafts each rebuild the same headless-operation runbook from scratch:
service-account auth without an interactive `op` prompt, what `missing-user` means for a runner
(it warns and exits 0, but the sweep then exits 2, and since PR #613 `recurring --all` skips such a
checkout as "unconfigured" while the aggregate run still succeeds), and how to preflight a cron
host. The shared runbook is knowledge that exists independently of any of those three tickets.

Write it once — likely a new `coga/headless` context — and let the drafts reference it.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-11), classified `gap`.

Note the related `stale` finding on `coga/contexts/coga/secrets/SKILL.md`: it claims the SA token
makes "every `op://` ref" resolve, which is true for ticket `secrets:` frontmatter and false for
config values, which are not `op://`-aware at all. Fix that before writing a runbook on top of it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
