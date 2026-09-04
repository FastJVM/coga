---
name: code/with-review
description: Code change implemented by one agent, then peer-reviewed by the other agent (the one that didn't write it) before a PR is opened for the human's final review.
steps:
  - name: implement
    assignee: agent
    requires: branch
    skills:
      - code/implement
  - name: peer-review
    assignee: other-agent
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

The `implement` step runs under the ticket's `agent:` (the coder). The
`peer-review` step declares `assignee: other-agent`, which resolves to
the configured `[agents.*]` type that is *not* the coder — so a change
written by Claude is reviewed by Codex, and one written by Codex is
reviewed by Claude. The flip is automatic: `coga bump` rewrites
`assignee:` to the peer when it enters `peer-review`, and `open-pr`
flips back to the coder.

With two configured agent types, `other-agent` infers the only peer with no
extra config. With three or more, set `peer = "<type>"` on the coder's
`[agents.<type>]` table; the mapping is one-directional, so each coder that
uses this workflow needs its own peer. An absent or ambiguous peer fails loud
rather than guessing.

The `coga launch` supervisor auto-chains across these agent boundaries:
when a bump rotates `assignee:` from one agent to another (coder →
peer → coder), it relaunches the *next* agent as a fresh process under
the same supervisor — claude's REPL exits and codex's starts, or vice
versa. Each step is a clean session with a freshly composed prompt; it
only returns control to the human at the final `review` step (an
owner/human handoff), or on a terminal (`done`/`canceled`), `paused`, or
`blocked` state.

## implement

Agent step, owned by the `code/implement` skill. It declares `requires: branch`,
so `coga bump` refuses to advance until `branch:` and `worktree:` are recorded
under `## Dev` in the ticket copy of the checkout the bump runs from.

## peer-review

You are the *other* agent — you did not write this change. Review it
with whichever review tool you natively speak:

- **Claude**: run the `/code-review` slash command (default effort —
  *not* `ultra`) against the branch diff vs `main`.
- **Codex**: run `codex review --base <branch you forked from>`
  (usually `main`).

From the feature worktree on the recorded branch, apply must-fix
findings, skip nits, re-run `python -m pytest`, commit (e.g.
`peer-review: apply review findings`), then `coga bump <slug>` from the
primary checkout. If findings imply a design rethink, write to the
blackboard and escalate per your launch mode — ask the attending human,
or `coga block` in a queue run. Escalate the same way if your review tool
isn't on PATH.

**This is the last judgment step before the PR opens.** The next `open-pr` step
is agent-owned, but its remit is only to run the deterministic command and bump,
so anything needing review judgment must be done *here* before you bump:

- **Author the PR body.** Add a `## PR` section on the blackboard with the
  summary and a one-line test plan. The `coga open-pr` command uses it as the PR
  body (falling back to `## Description` if you skip it), so this is where the
  human-facing description is written.
- **Make the branch fresh, not just conflict-free.** Don't wait for a
  conflict: run `git fetch origin main && git rebase FETCH_HEAD` in the
  feature worktree unconditionally, resolve whatever surfaces, re-run
  `python -m pytest`, and commit. `coga open-pr` refuses unsafe material drift,
  and the next step is intentionally mechanical — this step is the last one
  that makes rebase decisions. If a conflict needs a call you can't make,
  escalate per your launch mode — ask the attending human, or `coga block`
  in a queue run.

Leave the branch clean and committed with commits ahead of `main`; `coga
open-pr` refuses to publish an empty branch.

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
