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
run `relay bump` to hand off to `implement`. If the design is wrong
enough to redo, relaunch the `design` step instead of bumping.

## review

Owner reviews the open PR. This is an owner-controlled gate. If an agent
is launched or asked to assist during this step, it may inspect the PR,
run verification, prepare or push explicitly requested fixes, and report a
recommendation. It must not merge the PR, delete the branch, run
`relay mark done`, or otherwise advance/close the
task unless the human explicitly says to do that for this PR.

The human owner decides whether to edit, request changes, push fixes, or
merge. After the human merges, the `autoclose-merged` recurring sweep
marks the task `done` on its next run (≤24h); to close it immediately,
run `relay mark done`.
