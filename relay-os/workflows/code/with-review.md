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
reviewed by Claude. The flip is automatic: `relay bump` rewrites
`assignee:` to the peer when it enters `peer-review`, and `open-pr`
flips back to the coder.

`other-agent` needs exactly two agent types configured to be
unambiguous. With one type, or three or more, the bump fails loud rather
than guessing — fix `relay.toml` or the ticket's `agent:` if you hit
that.

The assignee change at each boundary breaks the `relay launch`
supervisor's auto-chain, so every switch produces a clean session
boundary under the right agent without special handling.

## peer-review

You are the *other* agent — you did not write this change. Review it
with whichever review tool you natively speak:

- **Claude**: run the `/code-review` slash command (default effort —
  *not* `ultra`) against the branch diff vs `main`.
- **Codex**: run `codex review --base <branch you forked from>`
  (usually `main`).

From the feature worktree on the recorded branch, apply must-fix
findings, skip nits, re-run `python -m pytest`, commit (e.g.
`peer-review: apply review findings`), then `relay bump <slug>` from the
primary checkout. If findings imply a design rethink, write to the
blackboard and `relay panic` instead. If your review tool isn't on PATH,
`relay panic`.

## review

Human reviews the open PR on GitHub. The peer-review pass has already
applied its must-fix findings to the branch, so the diff you see is the
post-review state. Edit, request changes, push fixes, or merge when
satisfied. After merging, `automerge` bumps the task to `done` on your
next `git pull` (or `relay status`).
