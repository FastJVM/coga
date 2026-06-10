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

Owner reviews the open PR. Edit, request changes locally, or merge
when satisfied. After merging, run `relay bump` to mark the task done.
