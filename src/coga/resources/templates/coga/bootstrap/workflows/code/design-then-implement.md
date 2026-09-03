---
name: code/design-then-implement
description: A thin ticket is designed into a spec, cold-reviewed by another agent, approved by the owner, then implemented and opened as a PR for final owner review.
steps:
  - name: design
    assignee: agent
    skills:
      - code/design
  - name: evaluate-design
    assignee: other-agent
    skills:
      - code/review-design
  - name: review-design
    assignee: owner
  - name: implement
    assignee: agent
    requires: branch
    skills:
      - code/implement
  - name: open-pr
    assignee: agent
    requires: pr
    skills:
      - code/open-pr
  - name: review
    assignee: owner
    skills:
      - code/address-pr-comments
---

A step that declares `skills:` does **not** compose the `## <step>` section
below: Coga builds that step-specific layer from the declared skill files, and
the inline section is never read by the launched agent. The base prompt,
contexts, ticket-level skills, ticket body, and blackboard still compose
normally. Agent instructions therefore belong in the step's skills. Sections
here for a skilled step are human-facing framing only. Skill-less steps *do*
compose their section, so those bodies are load-bearing.

## review-design

Owner reviews the spec the `design` step wrote into `ticket.md` —
Description, Acceptance Criteria, Proposed Shape, Out of Scope — and
the cold peer's `## Evaluator review` on the blackboard. Answer anything under
`## Open Questions` and resolve every must-fix evaluator finding. Edit the
ticket directly to correct scope or approach, and record a disposition when a
finding is intentionally rejected. When the spec is right, run `coga bump` to
hand off to `implement`. If the design is wrong enough to redo, relaunch the
`design` step instead of bumping.

## implement

Agent step, owned by the `code/implement` skill. It declares `requires: branch`,
so `coga bump` refuses to advance until `branch:` and `worktree:` are recorded
under `## Dev` in the ticket copy of the checkout the bump runs from.

## open-pr

Agent step, owned by the `code/open-pr` skill: `coga open-pr <slug>` pushes the
recorded branch, opens the PR, and writes `pr:` back under `## Dev`. It declares
`requires: pr`, so `coga bump` holds the step until that line exists.

There is no peer/self-review step in this workflow, so the PR body falls back to
the ticket's `## Description` — the design spec the owner already reviewed —
unless the `implement` step leaves a `## PR` section on the blackboard.

## review

Owner-controlled gate. The human reviews the open PR and decides whether to
edit, request changes, push fixes, or merge. An agent launched to assist here
runs the `code/address-pr-comments` skill, which carries the do-not-merge and
do-not-bump rules for that assist.

After the human merges, the `autoclose-merged` recurring sweep marks the task
`done` on its next run (≤24h); `coga bump` closes it immediately.
