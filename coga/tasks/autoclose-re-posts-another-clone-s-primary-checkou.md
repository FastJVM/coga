---
title: Autoclose re-posts another clone's primary checkout forever
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
agent: claude
---

## Description

Filed by Dream 2026-W40, Phase 6, routing the unresolved adjacent bug that Dream's Phase 4 Retro preserved in knowledge PR #920 ("New context: another clone's primary checkout never leaves the autoclose worklist", target `docs/contexts/dev/checkout-cleanup/SKILL.md`), from the done tickets `clean-up-all-the-working-trees` and `recurring/autoclose-merged`. Six autoclose `retires.md` entries record `/home/n/Code/coga` or `/home/n/Code/codex/coga` as their worktree; both are live primary checkouts of separate FastJVM/coga clones. The sweeping clone classifies them `standalone`, so they never discharge and are re-posted to coga-important on every run, and the `autoclose.py` remedy tells a human to "inspect and remove it by hand", i.e. delete an actively used clone. `is_primary_checkout` exempts only this repo's own primary, and `worktree_owner` records no owner for standalone clones. Fix so another clone's primary checkout is recognized (and discharged or reported without a delete remedy), then update the known-failure-mode text PR #920 adds. No open ticket owns this.

## Context

<!-- coga:blackboard -->

## Dev
branch: fix-autoclose-clone-primary

## Implementation handoff

Implemented primary-checkout preservation and foreign branch ownership:
- `src/coga/git.py` + `classify_checkout` returns `foreign-primary` with the
  owning root for independent repositories; topology never guesses whether a
  clone is disposable.
- `src/coga/retire_worklist.py` + `is_primary_checkout`, `worktree_owner`, and
  `owner_branch_remains` exempt primary directories and resolve legacy missing
  owners before judging branches. Entries clear only once their own clone's
  branch is gone; unreadable owners/branch lists remain pending.
- `src/coga/autoclose.py` + `ClosedTicket`, `_try_bump_one`, and
  `_dispose_checkouts` retain ownership across primary-directory filtering and
  use report-only branch handling for foreign primaries. No same-named branch
  in the sweeping clone is deleted, and no primary-directory delete remedy is
  offered.
- Updated `dev/checkout-cleanup` (replacing the unresolved failure mode) and
  the autoclose sweep skill, including both packaged twins. Independent `/tmp`
  clones receive the same protection: directory removal is optional operator
  cleanup, not required worklist debt.

Regression tests cover fresh closures and legacy ownerless entries, repeated
sweeps without reposting after branch deletion, same-named local branches,
local data preservation, linked control-checkout invocation, and unreadable
branch lists. The four new regression cases failed before implementation.

## Adjacent finding (unresolved)

Foreign linked worktrees and manual `coga retire` still reach
`src/coga/checkout_disposal.py` + `dispose_checkout`, which calls
`delete_branch(cfg, root, ...)` even after the worktree proof refuses a foreign
repository. A same-named branch in the invoking clone can therefore be judged
for deletion instead of the foreign branch. Evidence: `_dispose_checkouts`
leaves existing foreign-linked directories on that shared path, and
`src/coga/commands/retire.py` + `_cleanup_checkout` passes recorded Dev values
directly to it. This ticket guards autoclose's foreign-primary path; the broader
disposal ownership issue remains outside scope. No follow-up ticket identified.

## Verification and delivery

- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_retire_worklist.py tests/test_autoclose_dispose.py -q -k 'another_clones_primary'`: 4 failed before the fix, as expected.
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_retire_worklist.py tests/test_autoclose_dispose.py tests/test_autoclose.py tests/test_git.py -q`: 280 passed.
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest`: 3139 passed in 197.60s, including packaged-twin checks.
- `git diff --check`: passed.
- Pushed commit `9c74a6013` on `fix-autoclose-clone-primary`. It contains current
  `origin/main`; the final rebase added only this session's already-published
  ticket/log bookkeeping, with identical implementation and tests.
- Launch checkout returned to clean `main` before this handoff. No PR opened.
  No task-layout, prompt-composition, workflow, or validation behavior changed,
  so the example fixture did not need edits.
