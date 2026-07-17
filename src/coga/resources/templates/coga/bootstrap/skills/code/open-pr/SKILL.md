---
name: code/open-pr
description: Agent step that runs `coga open-pr` to push the branch and open (or ready) the PR, then bumps. The deterministic push/open/record work lives in the command; the step gates on a recorded `pr:`, so it cannot complete without a real PR.
---

# Push and open the PR

This is an agent step, but the mechanical work — push, open (or ready) the PR,
record the URL — is done by a single deterministic command, `coga open-pr`. You
run it, confirm it recorded the PR, then bump. The *judgment* (what the PR says,
whether the branch is mergeable) belongs to the earlier implement / peer-review
steps; this step just turns the recorded branch into a PR.

The step declares `requires: pr`, so `coga bump` refuses to advance until a
`pr:` line is recorded under `## Dev`. That is a **data check**: skipping
`coga open-pr` and bumping anyway fails loud — the recorded artifact is the
gate, not your say-so.

## Order of operations

1. **Confirm the handoff state.** Read `branch:` / `worktree:` under `## Dev` on
   the blackboard. The implement / peer-review steps must have created the
   feature branch, recorded it, and left it committed and ahead of the base
   branch. If `branch:` / `worktree:` are missing, that is an earlier-step gap —
   `coga block` with a one-line reason rather than improvising a branch here.
2. **Return to the primary control checkout and run `coga open-pr <slug>`.**
   Task resolution and the `pr:` blackboard write belong to the control
   checkout; running from the feature worktree fails loud rather than updating
   a stale ticket copy. The deterministic command:
   - reads `branch:` / `worktree:` from `## Dev`,
   - confirms the worktree is on that branch, clean, ahead of the base
     (`[git].control_branch`, default `main`), and has no unsafe material drift
     from the latest `<remote>/<base>`,
   - pushes the branch by name (using an explicit force-with-lease when a safe
     retry follows a rebase),
   - opens the PR with `gh pr create` — or `gh pr ready` if a draft already
     exists, or reuses an already-open PR (idempotent on re-run),
   - writes `pr: <url>` back under `## Dev`.

   It operates on the recorded feature branch **by name** while the command
   stays in the control checkout — this is what retires the cross-worktree
   divergence trap. It **fails loud** (non-zero, nothing pushed/opened) on: no usable
   `branch:` / `worktree:`, a missing worktree, the worktree on the wrong branch
   or dirty, **no commits ahead of base** (the incident case — no empty PR), a
   stale branch, or a `git push` / `gh` auth failure.

   **PR title** = the ticket title. **PR body** comes, in order, from: a `## PR`
   section (blackboard first, then ticket body), else the ticket's
   `## Description`, else the title; a `Closes ticket: <slug>` line is always
   appended. So author a `## PR` section in the earlier steps if you want a
   curated summary + test plan; omitting it is fine.
3. **Bump.** Once `coga open-pr` reports the URL and `pr:` is recorded under
   `## Dev`, run `coga bump <slug>` to hand off to the next step. The bump's
   `requires: pr` gate will pass because the URL is now recorded.

## If `coga open-pr` fails

Fix the cause and re-run it — it is idempotent:

- Missing `branch:` / `worktree:` or a torn-down worktree → an earlier step
  didn't record/keep it; `coga block` if you can't recover it here.
- Nothing committed ahead of base → implement/peer-review produced no change;
  build it (or `coga block`) rather than opening an empty PR.
- Stale branch → rebase the control branch in the feature worktree, re-run
  `python -m pytest`, commit, return to the control checkout, then re-run
  `coga open-pr`. If an earlier attempt already pushed, the retry republishes
  the rewritten branch with an explicit force-with-lease.
- `git` / `gh` auth failure → follow the setup hint the command prints (fix the
  remote, load your SSH key / credential helper, `gh auth login`), then re-run.

## Acceptance for this step

- `coga open-pr <slug>` has been run and `pr: <url>` is recorded under `## Dev`.
- `coga bump <slug>` has advanced the workflow (its `requires: pr` gate passed).

## What this skill does NOT do

- Decide whether to merge — that's the human's job in the next step.
- Make code changes or resolve CI failures. If CI fails for a real reason,
  `coga block` and let the human relaunch.
- Resolve merge conflicts with the base — the peer-review / self-qa step handles
  mergeability before this step runs.
- Edit `assignee:` by hand. The workflow's per-step `assignee:` handles the role
  rewrite on bump.
