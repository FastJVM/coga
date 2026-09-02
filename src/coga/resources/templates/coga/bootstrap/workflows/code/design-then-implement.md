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
below: Coga builds that step's prompt from the skill file alone, and the inline
section is never read by the launched agent. Agent instructions therefore belong
in the skill. Sections here for a skilled step are human-facing framing only.
Skill-less steps *do* compose their section, so those bodies are load-bearing.

## review-design

Owner reviews the spec the `design` step wrote into `ticket.md` —
Description, Acceptance Criteria, Proposed Shape, Out of Scope — and
answers anything under `## Open Questions` on the blackboard. Edit the
ticket directly to correct scope or approach. When the spec is right,
run `coga bump` to hand off to `implement`. If the design is wrong
enough to redo, relaunch the `design` step instead of bumping.

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
