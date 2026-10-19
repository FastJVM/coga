---
name: dev/code
description: Overview of conventions for code tickets (tickets whose workflow produces a branch and PR), linking the checkout, `## Dev` record, and cleanup topics plus the blackboard's superseded-designs convention; attach it to any such ticket.
---

# Code-task conventions

Code tickets produce a Git branch and usually a pull request. The link from
ticket to branch to PR is recorded explicitly rather than inferred from the
slug, because slug conventions break whenever a PR bundles tickets, an agent
picks another branch name, or a slug is truncated. Anything that follows the
link (bump gates, `open-pr`, autoclose, retire, status views) reads the
record directly.

## The rules in brief

- **Work in the launch checkout; start and end on `main`.** No linked
  worktrees. `coga launch` prepares each shipped step's checkout — creating
  or reusing the recorded branch, or staying on control — and returns it
  afterwards; the runtime notice says which. Elsewhere the agent performs
  the same moves itself. An occupied checkout means stop and ask (or block).
  The sandbox clone is the one fallback. See
  [dev/checkouts](../checkouts/SKILL.md).
- **`## Dev` is the record.** `branch:` (written and published by launch
  for a new branch), `worktree:` only for a sandbox clone, `pr:` from `coga
  open-pr`. See [dev/checkouts](../checkouts/SKILL.md), which also covers
  stranded ticket writes.
- **Leave branch cleanup to retire.** `coga retire` and the autoclose sweep
  delete the landed branch (and any leftover recorded worktree) under shared
  proofs. See
  [dev/checkout-cleanup](../checkout-cleanup/SKILL.md).
- **Keep the body current.** Archive abandoned plans in one
  `## Superseded designs` blackboard section. See
  [coga/blackboard](../../coga/blackboard/SKILL.md#superseded-designs).

## Not covered

- **Commit message style**: follow the repo's existing convention.
- **Branch naming**: no requirement to match the slug; the record makes the
  link explicit.
- **PR description shape**: owned by the workflow step's skill.
- **Changing the stored ticket format**: a branch that rewrites committed
  `coga/tasks/**` with the code that reads them follows the stored-ticket
  schema conversion rules in
  [coga/internals/git-regressions](../../coga/internals/git-regressions/SKILL.md#shipping-a-stored-ticket-schema-conversion).
- **Working on Coga's own source**: see
  [coga/codebase](../../coga/codebase/SKILL.md).
