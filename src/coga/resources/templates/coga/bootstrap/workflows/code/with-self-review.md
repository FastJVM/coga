---
name: code/with-self-review
description: Code change with an agent self-QA pass (/code-review + /simplify, fixes committed in place) before the PR is opened, so the human reviewer sees one clean diff. Three agent steps then human PR review.
steps:
  - name: implement
    assignee: agent
    requires: branch
    skills:
      - code/implement
  - name: self-qa
    assignee: agent
    skills:
      - code/self-qa
  - name: pr
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

## already-satisfied

If the implement or self-qa agent verifies that every requested item already
landed elsewhere and there is no branch, diff, or PR to create, the agent
closes the ticket with `coga mark done <slug>`.

The agent must write concrete evidence under `## Already satisfied` on the
blackboard first. This is the only direct agent close path in this workflow;
ordinary code changes still go through implement, self-QA, PR, and the
owner-controlled review gate. A missing decision or ambiguous verification is a
real blocker (`coga block`), not an already-satisfied closure.

## implement

Agent step, owned by the `code/implement` skill. It declares `requires: branch`,
so `coga bump` refuses to advance until `branch:` and `worktree:` are recorded
under `## Dev` in the ticket copy of the checkout the bump runs from.

## pr

Agent step, owned by the `code/open-pr` skill: `coga open-pr <slug>` pushes the
recorded branch, opens (or readies) the PR, and writes `pr:` back under
`## Dev`. It declares `requires: pr`, so `coga bump` holds the step until that
line exists.

The command is deterministic and has no judgment of its own, which is why the
preceding `self-qa` step is the one that authors the PR body and rebases the
branch.

## review

Owner-controlled gate. The human reviews the open PR on GitHub; the diff has
already been through `/code-review` and `/simplify` in the `self-qa` step, so
the agent QA is done. The human decides whether to edit, request changes, push
fixes, or merge. An agent launched to assist here runs the
`code/address-pr-comments` skill, which carries the do-not-merge and do-not-bump
rules for that assist.

After the human merges, the `autoclose-merged` recurring sweep marks the task
`done` on its next run (≤24h); `coga bump` closes it immediately.

`done` is not the end of the ticket. Its feature checkout and branch, recorded
under `## Dev`, outlive the close: neither the sweep nor `coga bump` disposes
of them, because destructive behavior is never implicit. The closing act is
the owner's — once the ticket is `done`, run `coga retire <slug>`. Retire
attempts a best-effort cleanup: it removes the recorded worktree and prunes
the landed branch only after proving that is safe, and otherwise preserves
them — a dirty, locked, missing or mismatched checkout, one shared with
another live ticket, or a run made off the control branch all skip cleanup.
Either way it then scaffolds and launches the `retro/done-ticket` task that
carries what the ticket learned into the knowledge base and deletes the
ticket, so a preserved checkout and branch can outlive the ticket and remain
the owner's follow-up work. Until someone runs it, the `done` ticket and its
stale checkout stay in the repo; see `coga retire` in the
`dev/checkout-cleanup` context for what it proves and refuses.
