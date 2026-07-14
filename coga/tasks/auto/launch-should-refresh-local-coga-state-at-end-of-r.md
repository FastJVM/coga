---
slug: auto/launch-should-refresh-local-coga-state-at-end-of-r
title: Launch should refresh local coga state at end of run
status: in_progress
mode: agent
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
secrets: null
script: null
step: 1 (implement)
---

## Description

When a `coga launch` run ends (bump handoff, mark done, block, or agent exit),
the checkout the launch was run from should be refreshed so its `coga/` state
matches what the run just published to the control branch — the ticket that was
worked, `coga/log.md`, and any other `coga/tasks/**` state that landed on
`origin/<control>` during the run. Today the sync is publish-only:
`src/coga/git.py` lands task state on the control branch (and fast-forwards the
local control *ref* best-effort), but its own docs note that a checkout on any
other branch "stays stale after every launch until a manual pull". The operator
who just watched a launch finish then runs `coga status` in the same terminal
and sees a stale world — the completed step is missing or shown at an old step,
with no signal that the view is stale.

Scope:

- At the end of a launch run (all exit paths the supervisor sees), fetch
  `origin/<control>` and update the launch checkout's `coga/` subtree —
  `coga/tasks/**` and `coga/log.md` (union-merge for the log) — from it.
  Working-tree product files outside `coga/` are never touched.
- The refresh must be safe on a feature-branch checkout: it updates the
  `coga/` files (committing on the current branch the same way mid-run ticket
  sync already does), not the branch's source tree.
- Failure to refresh is non-fatal but loud (stderr + log), matching the
  existing mid-run sync-miss posture.
- Complementary, if cheap: `coga status` warns when the remote-tracking
  `origin/<control>` ref has newer `coga/tasks/**` than the checkout —
  comparing local refs only, no fetch, so status stays read-only/no-network.

## Context

Observed 2026-07-13: a launch running in a worktree bumped
`install/recommend-virtualenv-not-system-python` to step 4 and published the
state to `origin/main` correctly, but the operator's checkout (on a feature
branch) still showed the ticket at step 1/active and `coga status install`
rendered the stale table with no warning. Same root cause made the stuck
`install/document-where-to-run-init-and-adopt-existing-repo` open-pr failure
harder to spot. The publish half of the sync is verified working; this ticket
adds the missing pull-back half at the one place that already owns network
access and the run lifecycle — the launch supervisor.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
