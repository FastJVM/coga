---
name: dev/code
description: Overview of conventions for code tickets (tickets whose workflow produces a branch and PR), linking the checkout, `## Dev` record, cleanup, and design-history topics; attach it to any such ticket.
---

# Code-task conventions

Code tickets produce a Git branch and usually a pull request. The link from
ticket to branch to PR is recorded explicitly rather than inferred from the
slug, because slug conventions break whenever a PR bundles tickets, an agent
picks another branch name, or a slug is truncated. Anything that follows the
link (bump gates, `open-pr`, autoclose, retire, status views) reads the
record directly.

## The rules in brief

- **Pick a checkout layout and record it.** A single checkout on the feature
  branch is the default; use a separate feature checkout beside a
  control-plane primary checkout only when asked or when the primary checkout
  cannot host the branch. The agent moves itself; launch never changes its cwd.
  Seed `coga.local.toml` and agent discovery links in any fresh checkout.
  See [dev/checkouts](../checkouts/SKILL.md).
- **Record `## Dev` early and in the right copy.** `branch:` when the branch
  exists, `worktree:` when the checkout exists, `pr:` from `coga open-pr`.
  Write them where you will run `coga bump`. See
  [dev/dev-record](../dev-record/SKILL.md), which also covers stranded ticket
  writes and the review step.
- **Do not remove your own checkout.** `coga retire` and the autoclose sweep
  dispose of it under shared proofs. See
  [dev/checkout-cleanup](../checkout-cleanup/SKILL.md).
- **Keep the body current.** Archive abandoned plans in one
  `## Superseded designs` blackboard section. See
  [dev/design-history](../design-history/SKILL.md).

## Not covered

- **Commit message style**: follow the repo's existing convention.
- **Branch naming**: no requirement to match the slug; the record makes the
  link explicit.
- **PR description shape**: owned by the workflow step's skill.
- **Changing the stored ticket format**: a branch that rewrites committed
  `coga/tasks/**` with the code that reads them follows the stored-ticket
  schema conversion rules in [coga/sync](../../coga/sync/SKILL.md).
- **Working on Coga's own source**: see
  [coga/codebase](../../coga/codebase/SKILL.md).
