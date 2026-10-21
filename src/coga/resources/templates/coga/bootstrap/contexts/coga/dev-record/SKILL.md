---
name: coga/dev-record
description: Compatibility pointer for tickets that still attach `coga/dev-record`; states the `## Dev` linkage shape and links the topics that now own its write timing, gates, PR publication, stranded-write repair, and review-step rules.
---

# The `## Dev` record

This topic remains so tickets that still list `coga/dev-record` keep
resolving. New tickets do not need to attach it.

A code ticket records its linkage near the top of its blackboard:

```
## Dev
branch: <branch-name>
pr: <full /pull/<number> URL>
```

`worktree: <path>` is added only for a sandbox clone. One field per line,
current values rewritten in place; a backtick-wrapped value may carry a
trailing note. The first `branch:` is the workflow checkout.

- Write timing, publishing `branch:` from `main`, and stranded ticket writes:
  [coga/checkouts](../checkouts/SKILL.md).
- `requires: branch` / `requires: pr`, branch-gate scope, and the review step:
  [coga/workflows](../workflows/SKILL.md).
- `coga open-pr` and record parsing:
  [coga/pr-publication](../pr-publication/SKILL.md).
- Terminal branch ownership: [coga/checkout-cleanup](../checkout-cleanup/terminal-owners/SKILL.md).
