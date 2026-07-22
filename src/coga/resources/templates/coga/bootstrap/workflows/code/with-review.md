---
name: code/with-review
description: Code change implemented by one agent, then peer-reviewed by the other agent (the one that didn't write it) before a PR is opened for the human's final review.
steps:
  - name: implement
    assignee: agent
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
---

## Peer review by the other agent

The `implement` step runs under the ticket's `agent:` (the coder). The
`peer-review` step declares `assignee: other-agent`, which resolves to
the configured `[agents.*]` type that is *not* the coder — so a change
written by Claude is reviewed by Codex, and one written by Codex is
reviewed by Claude. The flip is automatic: `coga bump` rewrites
`assignee:` to the peer when it enters `peer-review`, and `open-pr`
flips back to the coder.

`other-agent` needs exactly two agent types configured to be
unambiguous. With one type, or three or more, the bump fails loud rather
than guessing — fix `coga.toml` or the ticket's `agent:` if you hit
that.

The `coga launch` supervisor auto-chains across these agent boundaries:
when a bump rotates `assignee:` from one agent to another (coder →
peer → coder), it relaunches the *next* agent as a fresh process under
the same supervisor — claude's REPL exits and codex's starts, or vice
versa. Each step is a clean session with a freshly composed prompt; it
only returns control to the human at the final `review` step (an
owner/human handoff), or on a terminal (`done`/`canceled`), `paused`, or
`blocked` state.

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

Follow the `code/open-pr` skill: run `coga open-pr <slug>` from the checkout that
owns the live ticket, then `coga bump`. That is the primary control checkout for
a separate recorded worktree, or the recorded primary checkout on its feature
branch for the single-checkout layout.
The command is deterministic — it reads `branch:` / `worktree:` from `## Dev`,
confirms the recorded checkout is on that branch, clean, ahead of `main`, and
not stale, pushes, opens the PR (`gh pr create`, or `gh pr ready` for an
existing draft), and writes `pr: <url>` back under `## Dev`. It pushes the
recorded feature branch **by name** and, in the single-checkout layout, commits
and pushes the generated ticket write so the branch remains clean.

This step declares `requires: pr`: `coga bump` refuses to advance until `pr:` is
recorded under `## Dev`. So a skipped or failed `coga open-pr` (missing `## Dev`
fields, nothing committed ahead of `main`, a stale branch, or a git/`gh` auth
problem) leaves the step put — the gate is a **data check** on the recorded PR,
not a matter of the agent's say-so. Fix the cause and re-run `coga open-pr`
(it's idempotent), or `coga block`. That is what makes the step require a real
PR by construction. On a successful single-checkout bump, the gate republishes
the post-transition ticket commit to the PR branch so it stays mergeable with
the control copy.

## review

Human reviews the open PR on GitHub. The peer-review pass has already
applied its must-fix findings to the branch, so the diff you see is the
post-review state.

This is an owner-controlled gate. If an agent is launched or asked to
assist during this step, it may inspect the PR, run verification, prepare
or push explicitly requested fixes, and report a recommendation. It must
not merge the PR, delete the branch, run
`coga mark done`, or otherwise advance/close the task unless the human
explicitly says to do that for this PR.

The human owner decides whether to edit, request changes, push fixes, or
merge. After the human merges, the `autoclose-merged` recurring sweep
marks the task `done` on its next run (≤24h); to close it immediately,
run `coga mark done`.
