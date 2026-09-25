---
title: Run the landed-branch sweep daily from autoclose
status: in_progress
owner: nicktoper
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (self-qa)
agent: claude
---

## Description

Local branches for merged PRs pile up for up to a week. On 2026-09-24 this checkout held 49 local branches: 41 with merged PRs, 1 closed, and 20 worktree registrations pointing at wiped /tmp paths. Daily autoclose only disposes of checkouts that a ticket recorded. Ad-hoc branches and worktrees (review checkouts such as /tmp/coga-review-eight/pr873, agent scratch worktrees) are left to the weekly Monday branch-sweep, so a PR merged on Tuesday leaves its branch for six days, and longer if the sweep hits a pinned worktree. Make autoclose's daily run also apply branch-sweep's landed-branch pass (git worktree prune, then delete local and remote branches whose PR merged or closed, under the existing proofs in branchcleanup/branchsweep: no open PR, tip landed or equal to the merged PR head modulo Coga bookkeeping commits, pristine unclaimed worktree). Either fold the pass into autoclose-merged or schedule branch-sweep daily; decide which, and update dev/checkout-cleanup and coga/recurring/scheduling. Tradeoff to weigh: the weekly cadence was deliberate (daily = ticket-recorded checkouts, weekly = GC of everything else), and a daily pass adds gh API calls to every autoclose run. Done when a branch whose PR merged, with no live ticket, is gone locally and on origin after the next daily autoclose, and branches with unpushed non-bookkeeping commits are still reported, not deleted.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: daily-autoclose-branches
worktree: /home/n/Code/codex/coga

## Implementation decisions

- Owner explicitly requested continuing in this workdir; the temporary `coga-control` worktree was removed. The prior branch remains intact. Task-state edits were preserved with stash `daily-autoclose-checkout-transition`; tracked edits applied successfully (the Python-floor ticket already matched main). The untracked copy of this ticket could not apply over its published copy; its obsolete control-checkout handoff is superseded here. Stash retained as a recovery copy.
- Owner approved chaining the registered branch-sweep recipe after successful autoclose in the recurring `ticket.py`. Reuse existing proofs and reports; accept daily GitHub queries, retain the weekly retry. No deletion policy expansion: closed-but-unmerged PR status alone does not authorize deletion.
- `src/coga/autoclose.py` / `run_autoclose_recipe` owns recorded-ticket disposal; `src/coga/branchsweep.py` / `run_branch_sweep_recipe` provides the existing unrecorded-branch pass. Compose them at the recurring ticket edge; direct `coga run autoclose` stays scoped to its current recipe.

## Implementation and verification

- Daily `ticket.py` now runs `autoclose`, then `branch-sweep`, then bumps only after both succeed. Updated owning cleanup/scheduling topics, referring templates/skills/workflow, and all eight packaged twins.
- Added regression coverage for call order, failure propagation/reporting, and real local/bare-origin cleanup with no closing tickets: bookkeeping-only follow-ups are deleted; unpushed source commits retain both refs and are reported. The copied example fixture continues to exercise the headless period lifecycle.
- Before the fix: `.venv/bin/python -m pytest tests/test_recurring_shims.py -k autoclose_shim --no-header -q` showed the two expected failures (missing sweep and missing failure propagation), one pass.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_recurring_shims.py tests/test_branchsweep.py tests/test_autoclose_sweep.py tests/test_packaging.py -q`: 98 passed, 1 failed. Failure is existing `test_live_and_packaged_copies_stay_identical` phone-home runtime state drift (both files verified unchanged from HEAD); follow-up is PR #895, already named in the Python-floor ticket. All eight changed twins separately verified byte-identical. Asked attending owner whether to advance with this unrelated failure documented; do not fix it here.
- Example validation: from `example/coga`, `env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json`: 4 OK, no issues. The initial run without clearing inherited webhook variables refused configuration; the fixture intentionally has no webhook declaration.
- Ambient `python -m pytest` could not collect because that interpreter lacks `tomlkit`; use the existing `.venv/bin/python` test environment.
- First full run: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`: 2937 passed, 2 failed in 269.66s. Besides phone-home, `test_control_worktree_is_removed_and_unregistered_after_the_run` saw unrelated `/tmp/coga-recurring-repo-uqu3rjj8` via its global glob; the worktree created by that test was correctly removed. Rerun with `TMPDIR=/tmp/coga-daily-autoclose-tests` passed (1 passed in 2.49s), without changing code or touching that unrelated directory.
- Owner approved documenting the pre-existing phone-home failure and proceeding if the remaining checks pass.
- Implementation committed as `340171406` after rebasing on `origin/main` (`944d6dd4a`). Only live ticket/log state is dirty; no implementation work remains uncommitted. Final full-suite run uses the isolated `TMPDIR` above after rebase.
- Final verification: `TMPDIR=/tmp/coga-daily-autoclose-tests PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`: **2938 passed, 1 failed in 267.22s**. Sole failure is the owner-approved pre-existing phone-home twin drift, tracked by PR #895; the recurring cleanup check passed. `git diff --check` passed. Full output: `/tmp/coga-daily-autoclose-final.log`.
- Ready for self-QA. No push or PR performed in this step. Daily branch cleanup is wired through the existing registered recipe; standalone direct autoclose remains unchanged, and the weekly branch-sweep template remains available.

## Self-QA

- Confirmed primary checkout `/home/n/Code/codex/coga` on `daily-autoclose-branches`, implementation commit `340171406`; initial dirty files were only this ticket and CLI-written `coga/log.md` state.
- Review returned: completed the manual branch-diff review against `main` permitted when `/code-review` is unavailable. No actionable findings. Traced recipe ordering, failure reporting, report append behavior, recurring-report claim exclusions, and the existing local/remote cleanup gates; no review remains in flight.
- `/simplify` is not callable in this harness; performed its reuse, quality, and efficiency pass directly. No worthwhile simplifications: the script reuses both registered recipes without adding core machinery, and tests reuse existing Git fixtures. No implementation changes were needed.
- No changed interactive terminal, pager, or Slack rendering surface requires a manual visual sweep. Headless execution and branch/ref outcomes are exercised by the recurring lifecycle and bare-origin integration tests.
- Example validation: from `example/coga`, `env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json`: 4 OK, no issues. `git diff --check` passed.
- Full-suite rerun: `TMPDIR=/tmp/coga-daily-autoclose-tests PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`: **2938 passed, 1 failed in 277.48s**. The sole failure remains `tests/test_packaging.py::test_live_and_packaged_copies_stay_identical` for the unchanged phone-home twin runtime drift, already approved by the owner for proceeding and tracked by PR #895. Output: `/tmp/coga-daily-autoclose-self-qa.log`. No new regressions; ready for the PR step.
