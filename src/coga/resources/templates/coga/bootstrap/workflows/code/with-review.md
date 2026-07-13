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
owner/human handoff), or on `done`/`paused`/`blocked`.

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
blackboard and `coga block` instead. If your review tool isn't on PATH,
`coga block`.

**This is the last agent step before the PR opens** — `open-pr` is a
deterministic script, not an agent, so anything that needs judgment must be
done *here*, before you bump:

- **Author the PR body.** Add a `## PR` section on the blackboard with the
  summary and a one-line test plan. The `open-pr` script uses it as the PR
  body (falling back to `## Description` if you skip it), so this is where the
  human-facing description is written.
- **Make the branch mergeable.** Ensure the feature branch has no conflicts
  with the base (`main`): if it does, merge/rebase `main` in, resolve, re-run
  `python -m pytest`, and commit so the reviewer receives a clean, mergeable
  PR. If a conflict needs a judgment call you can't make, `coga block`.

Leave the branch clean and committed with commits ahead of `main`; the
`open-pr` script refuses to advance otherwise (it will not open an empty PR).

## open-pr

**Script step — no agent runs here.** The `code/open-pr` skill declares a
`script:`, so the launch supervisor runs it directly: it reads `branch:` /
`worktree:` from `## Dev`, confirms the worktree is on that branch, clean, and
ahead of `main`, pushes, opens the PR (`gh pr create`, or `gh pr ready` for an
existing draft), writes `pr: <url>` back under `## Dev`, and — on exit 0 — the
launcher advances to `review`.

Nothing to hand-run and no `coga bump` to remember. If the script exits
non-zero (missing `## Dev` fields, nothing committed, or a git/`gh` auth
problem) the step does **not** advance and a failure is posted — fix the cause
in the earlier steps and relaunch, or `coga block`. This is what makes the
step require a real PR by construction.

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
