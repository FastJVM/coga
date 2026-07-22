---
name: code/with-self-review
description: Code change with an agent self-QA pass (/code-review + /simplify, fixes committed in place) before the PR is opened, so the human reviewer sees one clean diff. Three agent steps then human PR review.
steps:
  - name: implement
    assignee: agent
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
---

## already-satisfied

If the implement or self-qa agent verifies that every requested item already
landed elsewhere and there is no branch, diff, or PR to create, the agent
closes the ticket with `coga mark done <slug>`.

The agent must write concrete evidence under `## Already satisfied` on the
blackboard first. This is the only direct agent close path in this workflow;
ordinary code changes still go through implement, self-QA, PR, and the
owner-controlled review gate. A missing decision or ambiguous verification is a
real blocker (`coga block`), not an already-satisfied closure.

## pr

Follow the `code/open-pr` skill: run `coga open-pr <slug>` from the checkout that
owns the live ticket, then `coga bump`. That is the primary control checkout for
a separate recorded worktree, or the recorded primary checkout on its feature
branch for the single-checkout layout.
The command is deterministic — it reads `branch:` / `worktree:` from `## Dev`,
confirms the recorded checkout is on that branch, clean, ahead of `main`, and
not stale, pushes, opens the PR (`gh pr create`, or `gh pr ready` for an
existing draft), and writes `pr: <url>` back under `## Dev`. It pushes the
recorded feature branch by name and, in the single-checkout layout, commits and
pushes the generated ticket write so the branch remains clean.

This step declares `requires: pr`: `coga bump` refuses to advance until `pr:` is
recorded under `## Dev`. So a skipped or failed `coga open-pr` (missing `## Dev`
fields, nothing committed ahead of `main`, a stale branch, or a git/`gh` auth
problem) leaves the step put — the gate is a data check on the recorded PR. Fix
the cause and re-run `coga open-pr` (it's idempotent), or `coga block`. That is
what makes the step require a real PR by construction. On a successful
single-checkout bump, the gate republishes the post-transition ticket commit to
the PR branch so it stays mergeable with the control copy.

Because `coga open-pr` is deterministic, anything needing judgment must be done
in the **preceding `self-qa` step**, before it bumps:

- **Author the PR body** — add a `## PR` section on the blackboard (summary +
  one-line test plan). `coga open-pr` uses it as the PR body, falling back to
  `## Description` if absent.
- **Make the branch fresh, not just conflict-free** — run `git fetch origin
  main && git rebase FETCH_HEAD` unconditionally (the `open-pr` script refuses
  a branch that is materially stale against `origin/main` even when it merges
  cleanly), resolve whatever surfaces, re-run `python -m pytest`, and commit.
  Leave the branch committed and ahead of `main`.

## review

Human reviews the open PR on GitHub. The PR diff has already been through
`/code-review` and `/simplify`, so the agent QA is done — your job is
the human-judgment gate.

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
