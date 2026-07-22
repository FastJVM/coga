---
slug: distill-git-conflict-errors-and-stop-compounding-d
title: Distill git conflict errors and stop compounding diverged-checkout failures
  in recurring sweeps
status: done
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
---

## Description

A `coga recurring --all ~/Code` sweep hit a diverged control checkout
(`claude/coga`: local `main` ~14 commits ahead with a ticket-file conflict
against `origin/main`). Coga correctly refused to scan (fail loud), but the
failure handling has three defects, observed in the 2026-07-20 sweep log:

1. **Quadruple error dump.** The identical rebase conflict is printed four
   times — the pre-scan catch-up note, the freshness-gate refusal, then after
   the child exits, `[git] refresh failed` (ff-only merge) and `[git] sync
   failed` (a second rebase) — each embedding raw `Rebasing (1/14)…` progress
   lines and git hint blocks. ~60 lines of spew for one fact.
2. **Each failed sweep deepens the divergence.** After the freshness gate
   refused, the launch wrapper still ran `sync_coga_state`, committing
   `Sync coga state` locally (the first rebase replayed 14 commits, the retry
   15). Every failed run adds a commit, growing the eventual manual resolve.
3. **The summary isn't actionable.** The parent ends with
   `1 repo(s) failed — see above` instead of naming the repo, the conflicting
   file(s), and the exact remediation command.

Fixes (scope agreed with owner):

- **A — distill git conflict errors.** In
  `recurring_runner._rebase_checked_out_branch_onto` and the `git.py`
  sync/refresh error paths, keep only the `error: could not apply <sha>
  <subject>` and `CONFLICT … <file>` lines from git output; drop progress and
  hint noise; append the one remediation command
  (`git -C <root> rebase <remote>/<control-branch>`).
- **B — short-circuit after the freshness-gate refusal.** A recurring-scan
  child that refuses before mutating period state must not be followed by the
  post-launch refresh + `sync_coga_state` for that repo: one concise error,
  zero new local commits.
- **C — actionable `--all` summary.** The parent's per-repo failure line names
  the conflicting file(s) and the exact fix command instead of "see above".

Out of scope (owner deferred): auto-resolving ticket-file conflicts by status
precedence; recurring queue guidance; `coga create` prefix guard.

## Context

**Shipped ahead of this ticket's workflow.** A–C were scoped with the owner
and implemented in a single attended orient session on 2026-07-20, before this
draft was ever launched. The change merged as
[PR #620](https://github.com/FastJVM/coga/pull/620) (`baa70a43` on `main`,
branch `claude/git-error-hygiene`), so the `implement` / `self-qa` / `pr` steps
have no work left to do. The ticket is closed as a record of the change.

What landed:

- **A (distill):** new `git.summarize_git_failure` keeps `error:`/`fatal:`/
  `CONFLICT` lines only (deduped, `\r`-progress aware, last-line fallback);
  wired into `_rebase_onto_remote`, `_run_git`, and recurring's
  `_rebase_checked_out_branch_onto`. `_sync_control_checkout_ahead` grew
  `announce_failure=` so the `--all` gate reports the conflict exactly once,
  and appends the resolve command (`git -C <root> rebase <remote>/<branch>`)
  only when the fetch succeeded — a fetch failure gets no rebase advice.
- **B (short-circuit):** the freshness refusal exits
  `git.STALE_CONTROL_EXIT_CODE` (**75**, EX_TEMPFAIL). Exit 3 was the first
  pick and was rejected: an existing test legitimately runs a user script that
  exits 3, so the code would collide. On 75, `launch` skips the post-exit
  control refresh — scoped to bootstrap scripts, since the exit-code contract
  is coga-owned and user scripts keep the unconditional refresh — and
  `cli.main` skips the end-of-command state sweep that previously stacked one
  local `Sync coga state` commit per failed run (the observed 14→15 growth).
- **C (summary):** the `--all` parent prints a cause-naming line for code-75
  children, and the final summary names each failed repo.

Contexts updated in the same change: `coga/sync` (live + packaged copies, gate
bullet) and packaged `coga/cli` (`--all` paragraph).

Verification: `python3.12 -m pytest` → 1370 passed, 1 skipped. New tests: 4 in
`test_git.py` (distiller + cli sweep skip), 3 in `test_recurring.py`
(real-divergence remediation, bare-sweep single note, parent naming), 2 in
`test_launch_script.py` (bootstrap skip vs user-script non-skip); 3 existing
gate tests updated to the new exit code.

Deferred by the owner, still unclaimed if anyone wants to pick them up:
auto-resolving ticket-file conflicts by status precedence (E), recurring queue
guidance (F), and a `coga create` prefix guard (D).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
