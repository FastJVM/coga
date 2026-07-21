---
slug: distill-git-conflict-errors-and-stop-compounding-d
title: Distill git conflict errors and stop compounding diverged-checkout failures
  in recurring sweeps
status: draft
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
step: 1 (implement)
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

<!-- coga:blackboard -->

## Dev

- branch: claude/git-error-hygiene
- pr: https://github.com/FastJVM/coga/pull/620

## Implementation notes (2026-07-20, attended orient session)

Scope A–C agreed with owner; implemented and verified in one pass.

- **A (distill):** new `git.summarize_git_failure` keeps `error:`/`fatal:`/
  `CONFLICT` lines only (deduped, `\r`-progress aware, last-line fallback);
  wired into `_rebase_onto_remote`, `_run_git`, and recurring's
  `_rebase_checked_out_branch_onto`. `_sync_control_checkout_ahead` grew
  `announce_failure=` so the `--all` gate reports the conflict exactly once,
  and appends the resolve command (`git -C <root> rebase <remote>/<branch>`)
  only when the fetch succeeded (a fetch failure gets no rebase advice).
- **B (short-circuit):** freshness refusal now exits
  `git.STALE_CONTROL_EXIT_CODE` (**75**, EX_TEMPFAIL — first pick was 3, but
  an existing test legitimately uses a user script exiting 3, proving the
  collision risk). On that code: launch skips the post-exit control refresh
  (scoped to bootstrap scripts — the exit-code contract is coga-owned, user
  scripts keep the unconditional refresh) and `cli.main` skips the
  end-of-command state sweep (which previously stacked one local `Sync coga
  state` commit per failed run — the observed 14→15 commit growth).
- **C (summary):** `--all` parent prints a cause-naming line for code-75
  children and the final summary names each failed repo.

Contexts updated in the same change: `coga/sync` (live + packaged copies,
gate bullet) and packaged `coga/cli` (`--all` paragraph).

Verification: `python3.12 -m pytest` → 1370 passed, 1 skipped. New tests:
4 in test_git.py (distiller + cli sweep skip), 3 in test_recurring.py
(real-divergence remediation, bare-sweep single note, parent naming), 2 in
test_launch_script.py (bootstrap skip vs user-script non-skip); 3 existing
gate tests updated to the new exit code.

Out of scope per owner: create-prefix guard (D), recurring queue guidance
(F), ticket-conflict auto-resolution (E).
