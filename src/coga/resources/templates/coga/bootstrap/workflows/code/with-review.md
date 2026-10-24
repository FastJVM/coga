---
name: code/with-review
description: Code change implemented by the main agent, then reviewed by its configured peer before a PR is opened for the human's final review.
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

## Peer review by the other agent

The `implement` step derives its operator from the ticket's `agent:` main-agent
choice. The `peer-review` step declares `assignee: other-agent`, which resolves
to that main agent's configured peer. `coga bump` advances `step:` and the next
operator is derived from the frozen role; it never writes an assignment.
`open-pr` declares `agent` and routes back to the same main-agent choice.

With two configured agent types, `other-agent` infers the only peer with no
extra config. With three or more, set `peer = "<type>"` on the main agent's
`[agents.<type>]` table; the mapping is one-directional, so each main agent that
uses this workflow needs its own peer. An absent or ambiguous peer fails loud
rather than guessing.

An explicit launch override changes the executing agent without changing the
stored main agent or its peer. It can therefore make the same agent implement
and review a change. Peer selection alone does not prove independent authorship.

The `coga launch` supervisor auto-chains across these agent boundaries:
when a bump changes the derived operator (main → peer → main),
it launches the *next* agent as a fresh process under
the same supervisor — claude's REPL exits and codex's starts, or vice
versa. Each step is a clean session with a freshly composed prompt; it
only returns control to the human at the final `review` step (an
owner/human handoff), or on a terminal (`done`/`canceled`), `paused`, or
`blocked` state.

## implement

Agent step, owned by the `code/implement` skill. Launch creates or reuses the
recorded branch before the agent starts (`coga/checkouts`). The step declares
`requires: branch`, so `coga bump` refuses to advance until `branch:` is
recorded under `## Dev` in the ticket copy of the checkout the bump runs from.

## peer-review

Other-agent step, owned by the `code/peer-review` skill: the main agent's
configured peer reviews the branch diff, applies must-fix findings, freshens
the branch, and prepares `## PR` before the mechanical `open-pr` step.

Older frozen snapshots of this workflow declare no step skill, so they compose
this section instead. In that case, read and follow the `code/peer-review`
skill — `coga/skills/code/peer-review/SKILL.md` when present, else the
installed bundled copy — as if it were composed here. Peer selection alone
does not prove independent authorship; that skill says what to record.

## open-pr

Agent step, owned by the `code/open-pr` skill: `coga open-pr <slug>` pushes the
recorded branch, opens (or readies) the PR, and writes `pr:` back under
`## Dev`. It declares `requires: pr`, so `coga bump` holds the step until that
line exists.

The command is deterministic and has no judgment of its own, which is why the
preceding `peer-review` step is the one that authors the PR body and rebases the
branch.

## review

Owner-controlled gate. The human reviews the open PR on GitHub; the peer-review
pass has already applied its must-fix findings, so the diff is the post-review
state. The human decides whether to edit, request changes, push fixes, or merge.
An agent launched to assist here runs the `code/address-pr-comments` skill,
which carries the do-not-merge and do-not-bump rules for that assist.

After the human merges, the `autoclose-merged` recurring sweep marks the task
`done` on its next run (≤24h); `coga bump` closes it immediately.

`done` is not the end of the ticket. When the sweep closes it, the sweep also
disposes of the feature branch (and any leftover recorded worktree) recorded
under `## Dev`, but only what the shared checkout proofs show is safe to
remove; a `coga bump` close disposes of nothing. The closing act is still the
owner's — once the ticket is `done`, run `coga retire <slug>`. Retire runs the
same proofs on whatever checkout remains, then deletes the done ticket with no
agent: its learning already landed with the merged PR. The packaged
`bootstrap/retire/ticket.md` owns that procedure, and the
`coga/checkout-cleanup` context owns what the shared proofs prove, preserve,
and record for later sweeps.
