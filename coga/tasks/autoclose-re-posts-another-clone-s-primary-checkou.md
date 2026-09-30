---
title: Autoclose re-posts another clone's primary checkout forever
status: blocked
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
step: 3 (open-pr)
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

## Peer review

- Tool: Claude `/code-review` (default effort) on `origin/fix-autoclose-clone-primary`
  vs `origin/main`. It **returned** with one finding, which I independently
  reproduced before it came back.
- Finding (must-fix, applied): a foreign-primary owner is the clone itself. Once
  an independent clone (for example a `/tmp` sandbox clone) was wiped,
  `branch_owner` → `None` read it as an "unreadable owner", so the entry was
  kept and re-posted to coga-important forever. That is the same bug class this
  ticket fixes; on `main` such an entry discharged.
- Fix (`872bfe52f`): `retire_worklist.owner_branch_remains` treats a gone owner
  that *is* the recorded `worktree:` as "branch gone". Autoclose now records the
  primary's path as `worktree:` on the worklist line (`worktree or owner`) so
  the two cases can be told apart. The docs (`dev/checkout-cleanup`,
  autoclose sweep skill, plus their packaged twins) and the module docstring
  are updated. A missing owner of a *foreign linked* worktree still keeps the
  entry, as before.
- New tests: `test_a_removed_independent_clone_takes_its_branch_with_it` and
  `test_a_wiped_sandbox_clone_clears_its_entry_without_reposting`. Both
  failed without the fix.
- No TTY/Slack-rendering surface changed beyond the remedy text already covered
  by tests.
- Branch rebased onto fresh `origin/main` (31 new commits, no conflicts); the
  full suite passed after the rebase: 3141 passed. `git diff --check` clean.
  Pushed with `--force-with-lease`. The work was done in a scratch clone
  because the launch checkout held another ticket's unpublished state. The
  launch checkout stays on `main`.
- The adjacent finding above (foreign-linked / manual `coga retire` branch
  ownership in `checkout_disposal`) is still out of scope.

## PR

Autoclose re-posted other clones' primary checkouts (`/home/n/Code/coga`,
`/home/n/Code/codex/coga`) to coga-important on every run and offered a
"remove it by hand" remedy that would delete an active clone.

- `git.classify_checkout` now calls another repository's primary checkout
  `foreign-primary`, with that checkout as its `owner`.
- `retire_worklist.is_primary_checkout` exempts every primary directory from
  directory debt. The branch half is judged in the owning clone, and legacy
  ownerless entries infer the owner first. Once the branch is gone there, the
  entry discharges without touching the directory. A wiped independent clone
  (for example a `/tmp` sandbox) also discharges, because its branch went
  with it.
- Autoclose never deletes a same-named branch in the sweeping clone for such a
  ticket, and the remedy text no longer suggests removing a primary checkout.
- Updated `dev/checkout-cleanup` (replacing the unresolved failure mode from
  #920) and the autoclose sweep skill, including their packaged twins.

Test plan: `python -m pytest` (3141 passed), including new regressions for
fresh and legacy entries, repeated sweeps without reposting, same-named local
branches, and wiped sandbox clones.

---

## Blockers

- [ ] [2026-09-30 11:07] [agent:claude] id=20260930T110756 open-pr start check failed: /home/n/Code/coga main is at origin/main but dirty with unpublished blackboard edits to another ticket, coga/tasks/autofix/make-branch-sweep-retirement-survive-an-existing-r/ticket.md (a 16-line '## Diagnosis (from recurring/autoclose-merged period agent, 2026-09-30)' note written 10:50). Not mine to commit or discard. Please publish or drop that note, then unblock; this step only needs to run 'coga open-pr' (branch fix-autoclose-clone-primary is pushed, peer review returned and its finding is fixed).
