---
slug: op/propagate-local-coga-config-into-worktrees
title: Propagate local Coga config into worktrees
status: draft
owner: zach
human: zach
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
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Make Coga-created and Coga-recommended feature checkouts usable for mutating
commands without manually rediscovering that `coga/coga.local.toml` is absent.
Linked worktrees and independent-clone fallbacks omit this gitignored file, so
commands that require an actor fail with exit 2 even though Coga instructed the
agent to create the checkout.

Define and implement one safe local-config handoff policy for these checkout
paths. A new checkout must inherit or initialize the required local identity
without committing `coga.local.toml`, exposing secret values, or silently
choosing a different actor.

## Context

- The packaged `code/implement` skill tells agents to create a linked worktree
  with `git worktree add`, or an independent clone under `/tmp` when `.git`
  metadata is read-only. Neither path carries ignored files.
- `bootstrap/open-pr/recipe.py` also tells an agent to recreate a missing
  recorded checkout with `git worktree add`.
- `config.py` deliberately requires `user` for commands that create or mutate
  task state. This guard is correct; the defect is that Coga's prescribed
  checkout flow does not satisfy it.
- The same seam must be covered by
  `v2/reintroduce-per-launch-worktree-isolation` if Coga resumes creating
  per-launch worktrees internally.
- There is precedent in the isolated Retro/Dream path for explicitly copying
  caller-local configuration before running Coga. Consolidate rather than add
  another one-off instruction.

Done means:

- every shipped workflow/skill or core path that creates a checkout establishes
  a usable, explicit actor identity before the first mutating Coga command;
- linked worktrees and independent-clone fallbacks are both covered;
- local config remains ignored and no credential value is logged, committed,
  or broadened into shared config;
- tests reproduce the fresh-worktree failure and prove the selected handoff
  policy; and
- live and packaged copies of changed workflow, skill, or context files remain
  synchronized.

Out of scope: weakening the requirement for an explicit actor. Execution-ready
validation of a separately provisioned runner belongs to sibling ticket
`op/fail-validation-when-local-user-is-required-for-ex`.
<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
