---
name: code/agent-merge
description: Code change implemented by the main agent, reviewed by its configured peer, then published and merged by the main agent with no owner gate. The owner audits after the merge and can revert.
steps:
  - name: implement
    assignee: agent
    requires: branch
    skills:
      - code/implement
  - name: peer-review
    assignee: other-agent
    skills:
      - code/peer-review
  - name: open-pr
    assignee: agent
    requires: pr
    skills:
      - code/open-pr
  - name: merge
    assignee: agent
    skills:
      - code/merge-pr
---

A step that declares `skills:` does **not** compose the `## <step>` section
below: Coga builds that step-specific layer from the declared skill files, and
the inline section is never read by the launched agent. The base prompt,
contexts, ticket-level skills, ticket body, and blackboard still compose
normally. Agent instructions therefore belong in the step's skills. Sections
here for a skilled step are human-facing framing only. Skill-less steps *do*
compose their section, so those bodies are load-bearing.

## When to use it

The same flow as `code/with-review`, except that the final step is the main
agent merging the PR instead of the owner reviewing it. The peer agent's
review is the review; the owner reads and, if needed, reverts the change after
it lands. Choose it only when the owner has accepted that trade for the
ticket or the repo. Pick `code/with-review` when the owner wants to read the
PR before it lands, and `code/with-self-review` when no peer resolves: this
workflow has no single-agent fallback, because a self-reviewed change merged
without an owner gate has had no second reader at all.

The `implement` → `peer-review` → `open-pr` steps behave exactly as in
`code/with-review`, and the `coga launch` supervisor chains main agent → peer
→ main agent → main agent without stopping. It returns control to the human
only on a terminal (`done`/`canceled`), `paused`, or `blocked` state.

## implement

Agent step, owned by the `code/implement` skill. Launch creates or reuses the
recorded branch before the agent starts (`coga/checkouts`). The step declares
`requires: branch`, so `coga bump` refuses to advance until `branch:` is
recorded under `## Dev` in the ticket copy of the checkout the bump runs from.

## peer-review

Other-agent step, owned by the `code/peer-review` skill: the main agent's
configured peer reviews the branch diff, applies must-fix findings, freshens
the branch, and prepares `## PR`. Peer selection alone does not prove
independent authorship; that skill says what to record. Because no owner
reads the PR before it lands, the `## Peer review` note — which review form
ran, that it completed or returned, what it found, and the head/base it
covered — is the evidence the `merge` step checks.

## open-pr

Agent step, owned by the `code/open-pr` skill: `coga open-pr <slug>` pushes the
recorded branch, opens (or readies) the PR, and writes `pr:` back under
`## Dev`. It declares `requires: pr`, so `coga bump` holds the step until that
line exists. Obligations the merge will not discharge are filed here, before
publication, exactly as on an owner-gated workflow.

## merge

Agent step, owned by the `code/merge-pr` skill. It starts on the recorded
branch, re-checks that the PR is open, ready, conflict-free, still at the
head the peer reviewed, and passing the repo's required verification at that
head, then merges it with the repo's merge method pinned to that head
(`gh pr merge --match-head-commit`) and runs `coga bump`, which marks the
ticket `done`. Any failed check is a refusal: the agent records why under
`## Merge` and escalates per its launch mode instead of forcing, repairing,
or bypassing branch protection. The owner then decides whether to fix and
re-run this step or move the ticket to an owner-gated workflow.

The owner's audit happens after the merge, from the bump's done message,
the merged PR, and the `## Merge` record. If an agent merged but the ticket
did not close, the `autoclose-merged` sweep (when scheduled) closes it on its
next run, since the ticket sits on its final step with a merged PR.

`done` is not the end of the ticket. A `coga bump` close disposes of nothing,
so the feature branch recorded under `## Dev` remains until the owner runs
`coga retire <slug>`, which runs the shared checkout proofs on whatever
checkout remains and then deletes the done ticket with no agent. The packaged
`bootstrap/retire/ticket.md` owns that procedure, and the
`coga/checkout-cleanup` context owns what the shared proofs prove, preserve,
and record for later sweeps.
