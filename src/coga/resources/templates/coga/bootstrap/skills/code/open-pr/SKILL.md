---
name: code/open-pr
script: run.py
description: Script step that pushes the branch and opens (or readies) the PR, then records the PR URL on the blackboard. Runs deterministically — no agent — so the step cannot complete without a real PR.
---

# Push and open the PR (script step)

This step is a **script**, not an agent checklist. The launch supervisor runs
`run.py` in place of an agent and advances the workflow **only if the script
exits 0**. A non-zero exit posts a failure and leaves the step put. That is the
point: the open-pr step cannot "complete" without producing a real PR, so no one
can bump past it with nothing built (the cross-worktree divergence incident).

Because the exit code — not an agent's judgment — gates the bump, there is
nothing to hand-run and no `coga bump` to remember: the launcher bumps for you.

## What the script does

1. Reads `branch:` / `worktree:` from the `## Dev` blackboard section (see the
   `dev/code` context).
2. Confirms the feature worktree is on that branch, is clean, and has commits
   ahead of the base branch (`[git].control_branch`, default `main`).
3. Pushes the branch (`git push -u <remote> <branch>`).
4. Opens the PR with `gh pr create` — or `gh pr ready` if a draft already exists
   for the branch, or reuses an already-open PR on a re-run (idempotent).
5. Writes `pr: <url>` back under `## Dev`.

**PR title** = the ticket title. **PR body** comes, in order, from: a `## PR`
section the agent authored on the blackboard (or in the ticket body), else the
ticket's `## Description`, else the title. A `Closes ticket: <slug>` line is
always appended. So the *judgment* (what the PR says) stays with the agent in
the earlier implement/peer-review steps; the *mechanics* (push, create, record)
are the script's.

## What the earlier agent steps must leave behind

The script consumes what implement/peer-review recorded. If those steps didn't:

- **`branch:` / `worktree:` under `## Dev`** — record them the moment the branch
  and feature worktree are created (per the `dev/code` context). Missing either
  → the script fails loud pointing at the gap.
- **committed work on the branch** — no commits ahead of base → the script fails
  loud rather than opening an empty PR. This is the incident case, caught by
  construction.
- **(optional) a `## PR` section** — a curated summary + test plan. Omitting it
  is fine; the script falls back to `## Description`.

## Failure modes (all fail loud, none advance the step)

- No `branch:` / `worktree:` recorded, or the worktree is gone → exit non-zero
  with the missing field named and a `coga block` hint.
- Worktree on the wrong branch, dirty, or no commits ahead of base → exit
  non-zero; nothing is pushed or opened.
- `git push` / `gh pr create` auth failure → exit non-zero with the
  `github_preflight` setup hint (fix the remote, load your SSH key / credential
  helper, `gh auth login`).

When the step fails, fix the cause (usually a missing `## Dev` field or an
un-committed change) and relaunch, or `coga block` if it needs a human decision.

## What this step does NOT do

- Decide whether to merge — that's the human's job in the next step.
- Make code changes or resolve CI failures.
- Resolve merge conflicts with the base — if the workflow needs that before
  handoff, the peer-review agent step handles it before this step runs.
