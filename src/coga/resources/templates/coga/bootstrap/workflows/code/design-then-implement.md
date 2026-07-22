---
name: code/design-then-implement
description: A thin ticket is designed into a spec by an agent, the owner reviews the spec, then an agent implements it and opens a PR for the owner to review and merge.
steps:
  - name: design
    assignee: agent
    skills:
      - code/design
  - name: review-design
    assignee: owner
  - name: implement
    assignee: agent
    skills:
      - code/implement
  - name: open-pr
    assignee: agent
    requires: pr
    skills:
      - code/open-pr
  - name: review
    assignee: owner
---

## review-design

Owner reviews the spec the `design` step wrote into `ticket.md` —
Description, Acceptance Criteria, Proposed Shape, Out of Scope — and
answers anything under `## Open Questions` on the blackboard. Edit the
ticket directly to correct scope or approach. When the spec is right,
run `coga bump` to hand off to `implement`. If the design is wrong
enough to redo, relaunch the `design` step instead of bumping.

## open-pr

Follow the `code/open-pr` skill: run `coga open-pr <slug>` from the checkout that
owns the live ticket, then `coga bump`. That is the primary control checkout for
a separate recorded worktree, or the recorded primary checkout on its feature
branch for the single-checkout layout.
The command reads `branch:` / `worktree:` from `## Dev`, confirms the recorded
checkout is on that branch, clean, ahead of `main`, and not stale, pushes, opens
the PR, and records `pr: <url>`. In the single-checkout layout it commits and
pushes that generated ticket write. This step declares `requires: pr`, so `coga
bump` refuses to advance until `pr:` is recorded — a skipped or failed `coga
open-pr` (nothing committed to PR, a stale branch, or broken auth) leaves the
step put. On a successful single-checkout bump, the gate republishes the
post-transition ticket commit to the PR branch so it stays mergeable with the
control copy. Fix the cause and re-run it (idempotent), or `coga block`.

There is no peer/self-review step here, so the PR body falls back to the
ticket's `## Description` (the reviewed design spec). If the `implement` step
wants a more specific body, it can write a `## PR` section on the blackboard;
otherwise the spec is used as-is.

## review

Owner reviews the open PR. This is an owner-controlled gate. If an agent
is launched or asked to assist during this step, it may inspect the PR,
run verification, prepare or push explicitly requested fixes, and report a
recommendation. It must not merge the PR, delete the branch, run
`coga mark done`, or otherwise advance/close the
task unless the human explicitly says to do that for this PR.

The human owner decides whether to edit, request changes, push fixes, or
merge. After the human merges, the `autoclose-merged` recurring sweep
marks the task `done` on its next run (≤24h); to close it immediately,
run `coga mark done`.
