---
name: coga/branch-sweep/sweep
description: Delete local and remote git branches whose work has already landed.
---

# Branch Sweep

Run `coga run branch-sweep` from the control checkout. The daily autoclose
period invokes it after autoclose; the weekly period is an independent retry.
It archives and deletes eligible local/remote refs and reports every refusal
under `## Branch Sweep` on the period blackboard (stdout outside a task).

Read [dev/checkout-cleanup](context:dev/checkout-cleanup) for the owning rules:
explicit Dev ownership, terminal owners with closed-unmerged PRs, merged
history, live claims and open PRs, source changes after closure, divergent
refs, checkout protections, and the `retired/<branch>` archive. Source changes
or unclear ownership need an owner decision; never infer abandonment from a
closed PR alone. Correct Dev records before retrying when a branch is still
needed by another ticket. No GitHub setting substitutes for these proofs.

A failed archive, ownership scan, worktree enumeration, or GitHub lookup
preserves affected work and makes the recipe fail. Inspect the report, fix the
named cause, then rerun the same command. Worktree-pinned refs remain pending.
The sweep sees only worktrees linked to its repository; branches owned by an
independent clone must be inspected in that clone. Never delete a primary
checkout as branch cleanup.
