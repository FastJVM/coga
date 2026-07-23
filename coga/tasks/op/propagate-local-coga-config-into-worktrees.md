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

Apply the existing Retro/Dream policy consistently: ordinary-copy the primary
checkout's complete `coga.local.toml` to the same repo-relative path in the
isolated checkout, restrict it to the current user, and never print, symlink,
snapshot, stage, or commit it. This intentionally carries the same
machine-local capabilities into another checkout on the same machine.

## Context

- The live and packaged `code/implement` skill tells agents to create a linked
  worktree with `git worktree add`, or an independent clone under `/tmp` when
  `.git` metadata is read-only. Neither path carries ignored files.
- Packaged `workflows/docs/with-review.md` has the same linked-worktree gap.
- `src/coga/resources/templates/coga/bootstrap/open-pr/recipe.py` tells an
  agent to recreate a missing recorded checkout with `git worktree add`, but
  does not mention local config.
- `config.py` deliberately requires `user` for commands that create or mutate
  task state. This guard is correct; the defect is that Coga's prescribed
  checkout flow does not satisfy it.
- Exact precedent: live and packaged `recurring/dream/ticket.md`,
  packaged `skills/retro/done-ticket/SKILL.md`, and
  `src/coga/resources/retire.md` already require an ordinary copy and cleanup.

Policy:

- Source is the primary checkout's valid `coga.local.toml`. If it is absent or
  invalid, fail loud before the first Coga command; never synthesize a user.
- If the destination file is absent, copy it byte-for-byte and set mode `0600`.
- If the destination already exists, preserve its contents when its parsed
  `user` equals the source actor, but tighten its mode to `0600`. If the actor
  differs, either file cannot be parsed, or permissions cannot be tightened,
  fail loud instead of overwriting or continuing.
- Apply the same rule on initial creation and resumed sessions. Remove copied
  config during teardown only for disposable checkouts whose owning flow
  already removes the checkout.

Done means:

- live and packaged `code/implement`, packaged `docs/with-review`, and
  `src/coga/resources/templates/coga/bootstrap/open-pr/recipe.py` establish or
  verify local config before the first mutating Coga command;
- linked worktrees and independent-clone fallbacks are both covered;
- the destination actor equals the source actor; a conflicting actor fails
  loud without overwriting either file;
- local config remains ignored and sentinel credential values never appear in
  output, snapshots, staged files, or commits;
- tests cover missing source, fresh destination, same-actor resume, conflicting
  actor, a same-actor destination with overly broad permissions, linked
  worktree, and independent-clone guidance; and
- live and packaged copies of changed workflow, skill, or context files remain
  synchronized.

Out of scope: weakening the requirement for an explicit actor. Execution-ready
validation of a separately provisioned runner belongs to sibling ticket
`op/fail-validation-when-local-user-is-required-for-ex`. Future internal
worktree automation remains owned by
`v2/reintroduce-per-launch-worktree-isolation`, which must preserve this
policy.
<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
