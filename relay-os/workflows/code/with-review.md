---
name: code/with-review
description: Code change implemented by an agent, then peer-reviewed by both Claude and Codex (in that order) before a PR is opened for the human's final review.
steps:
  - name: implement
    skills:
      - code/implement
  - name: claude-review
    skills:
      - code/claude-review
  - name: codex-review
    skills:
      - code/codex-review
  - name: open-pr
    skills:
      - code/open-pr
  - name: review
    assignee: owner
---

## Agent switching between steps

The two review steps are intentionally split so each runs under the
agent that natively speaks its review tool — `/code-review` is a Claude
Code slash command, `codex review` is a Codex CLI subcommand. The
workflow uses the generic `assignee: agent` resolution; switching the
*concrete* agent between steps is a human action:

1. After `implement` finishes, if the ticket's `agent:` is not already
   `claude`, edit it to `claude` (or pass `--agent claude` to
   `relay launch`) so the `claude-review` step runs in a Claude session.
2. After `claude-review` finishes, switch `agent:` to `codex` (or pass
   `--agent codex`) so `codex-review` runs in a fresh Codex session.
3. After `codex-review` finishes, either agent can do the mechanical
   `open-pr` step — leave the assignee as-is or switch back to whoever
   you prefer.

The `relay launch` supervisor's auto-chain breaks naturally on any
assignee change, so each switch produces a clean session boundary
without special handling.

## review

Human reviews the open PR on GitHub. Both agent passes have already
applied their must-fix findings to the branch, so the diff you see is
the post-peer-review state. Edit, request changes, push fixes, or
merge when satisfied. After merging, `automerge` bumps the task to
`done` on your next `git pull` (or `relay status`).
