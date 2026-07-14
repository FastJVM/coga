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

**Script step — no agent runs here.** The `code/open-pr` skill declares a
`script:`, so the launch supervisor runs it directly: it reads `branch:` /
`worktree:` from `## Dev`, confirms the worktree is on that branch, clean, and
ahead of `main`, pushes, opens the PR (`gh pr create`, or `gh pr ready` for an
existing draft), writes `pr: <url>` back under `## Dev`, and — on exit 0 — the
launcher advances to `review`.

Nothing to hand-run and no `coga bump` here. If the script exits non-zero
(missing `## Dev` fields, nothing committed ahead of `main`, or a git/`gh` auth
problem) the step does **not** advance and a failure is posted. This is what
makes the step require a real PR by construction.

Because `open-pr` is deterministic, anything needing judgment must be done in
the **preceding `self-qa` step**, before it bumps:

- **Author the PR body** — add a `## PR` section on the blackboard (summary +
  one-line test plan). The script uses it as the PR body, falling back to
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
