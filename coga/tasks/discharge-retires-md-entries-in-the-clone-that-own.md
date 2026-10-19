---
title: Discharge retires.md entries in the clone that owns them
status: done
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
agent: claude
---

## Description

Follow-up to run-clone-local-recurring-work-in-every-clone (owner decision 2026-10-16: kept out of that PR). Branch-sweep is now `scope: clone` and runs daily in every clone, but re-judging the autoclose-merged `retires.md` worklist still happens only in whichever clone services the repo-scoped autoclose-merged period. An entry whose `owner` is another clone (a foreign primary, or a foreign linked worktree) is reported for manual cleanup there and never discharges unless that clone happens to run autoclose. Wanted: a clone-scoped pass that judges and disposes of the entries owned by the sweeping clone, through the existing proofs in `checkout_disposal.dispose_checkout` and `retire_worklist`, and discharges them. Open design question: discharging edits `retires.md`, which is committed (`merge=union`, CAS-written). That breaks the 'clone scope commits nothing' property, so the pass needs its own publish path (for example `git.publish` of just that file, as upstream-coga does for its cursor). Related: autoclose-re-posts-another-clone-s-primary-checkou.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1035
branch: clone-discharge-retires

## Plan (owner-approved 2026-10-16)

- Fold the pass into the clone-scoped `branch-sweep` recipe (not a separate template): after `sweep_branches`, on control only, walk `retires.md` entries whose owner resolves to this clone (`retire_worklist.owned_here`), dispose via the backlog walker shared with autoclose, reconcile with `only=owned_here`, and `git.publish` just that file with `expect=` CAS on change. No log line, no new Slack.
- Tradeoff accepted: branch-sweep is no longer commit-free; docs state the one exception.

## Implement handoff (2026-10-16)

Commit `a1bfcc4dd` on `clone-discharge-retires`, pushed, rebased on origin/main `6cbf1e3cc`.

What changed:
- `retire_worklist.owned_here(root, entry)`: true only when the entry's *recorded* `owner` resolves (common dir) to `root`'s repo. Decided against owner inference: classifying from `root` never yields `root` itself, and ownerless lines' relative paths/branch names belong to the recording clone. Autoclose's reconcile backfills `owner` while the foreign dir exists, so normal entries carry one.
- `reconcile_worklist(..., only=)`: entries `only` rejects are kept verbatim (no discharge, no owner backfill, no ticket-branch read). `WorklistChange.original` = bytes read, for publish CAS.
- `autoclose.dispose_worklist_backlog(...)`: the backlog half of `_dispose_checkouts`, factored out with `include=` / `label=`; autoclose behavior unchanged (2 consumers now).
- `branchsweep.discharge_owned_followups`, called from `run_branch_sweep_recipe` after `sweep_branches`: control branch only (else skipped + noted); walks owned entries via the shared walker, reconciles with `only=owned_here`, and on a write runs `git.publish(cfg, [path], msg, expect={path: original})`. New result fields `followups_{disposed,preserved,discharged,skipped,failure}`; failure feeds `BranchSweepResult.failure` (exit 2). Report lists `disposed/preserved/discharged retire follow-up`. No Slack, no log line.
- Docs (live + packaged twins byte-identical): `coga/recurring/scheduling` (commit exception, removed "still done only by autoclose clone"), `dev/checkout-cleanup/foreign-ownership`, `coga/autoclose/sweep`, `coga/branch-sweep/sweep`; packaged `recurring/branch-sweep/ticket.md` (new step 7, dropped "no commit").

Adjacent (pre-existing, not fixed here): on origin/main the full suite already fails 4 tests — `test_packaging::test_live_and_packaged_copies_stay_identical`, `test_autoclose_sweep::test_autoclose_live_and_packaged_copies_stay_in_sync`, `test_upstream_coga::test_live_job_is_shaped_like_the_other_script_backed_jobs` (live `coga/recurring/{autoclose-merged,branch-sweep,upstream-coga}` were restored to pre-clone-scope by 28cba8f70 / PR #1032 and never re-synced after #1033 merged the packaged clone-scope versions), and `test_compose::test_coga_repo_instructions_carry_the_minimal_core_boundary[CLAUDE.md]` (likely from #1031 dropping root CLAUDE.md). Verified identical failures with my changes stashed. Related ticket: `state-sync-published-unmerged-recurring-templates`. Because the live branch-sweep template is stale, this repo's own clones won't run the new pass until the live templates are re-synced.

## Peer review

Direct Codex review **completed** on final head `87480d173906855eeebfb1ab78d780429466a6a4`, base `1d89f9fbc688ab47729dbcc49026347a7c11e467`. No unresolved findings in the final diff. The original Claude implementation received an independent direct review at rebased head `36ce55db0682bb1fadf5590022452792ae05cb67` against the same base; the final pass includes self-review of Codex's fixes. No nested reviewer CLI or other agent was used.

Two findings reproduced and fixed after the owner's approval in this attended session:
- A failed worklist publish left the local entry deleted. The next run made zero publish calls and reported success while control still held the entry. Reconcile and publish now share the state lock; transport, filesystem, and skipped-publication failures restore the original bytes when the file still holds this pass's rewrite. An intervening local edit is preserved and reported.
- With Git sync disabled, the pass still disposed/rewrote entries and reported a skipped publish as discharged. The follow-up pass now skips before disposal when Git sync is disabled, and `publish` returning `None` is a failure rather than a successful discharge.

Commit `87480d173` contains the fixes, regression coverage, synchronized context/skill twins, and source-comment corrections for the clone job's publication exception. The disposal proofs and recorded-owner-only policy remain the approved design. No TTY/pager/Slack rendering surface changed; plain recipe stdout was inspected during the scratch reproductions and checked by the recipe tests.

Verification completed:
- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest` on final head `87480d173906855eeebfb1ab78d780429466a6a4`, base `1d89f9fbc688ab47729dbcc49026347a7c11e467`: **3702 passed, 5 skipped, 4 failed** in 301.57s. The four failures match the independently reproduced main baseline below; none is introduced by this change.
- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest tests/test_branchsweep.py -k 'retire_follow or retire_discharge or discharge_publish or another_clone_updates'`: **8 passed, 134 deselected**. This ran at head `30124e797bdfd88adbce6a6429c0e4d7e757630d` plus the uncommitted final filesystem-error recovery patch, base `1d89f9fbc688ab47729dbcc49026347a7c11e467`; that identical working tree was committed as `87480d173`. The final full run covers these same cases again.
- `git diff --check origin/main...HEAD` on `87480d173` / `1d89f9fbc`: passed. All four changed context/skill twin pairs were also compared byte-for-byte and matched.
- The first full run on `36ce55db0682bb1fadf5590022452792ae05cb67`, base `1d89f9fbc688ab47729dbcc49026347a7c11e467`, returned 3696 passed, 5 skipped, and the same four failures. An intermediate run was stopped to add filesystem-error recovery and is not a verification receipt.

Tests use Python 3.12.12; the installed Python 3.11 lacks pytest, so the 3.11 floor was not exercised. No config, workflow, or task-model contract changed, so structural validation was not needed. Current main was fetched again after the final run and remained `1d89f9fbc`; the branch has two commits ahead and was pushed with `git push --force-with-lease origin clone-discharge-retires` (remote head `87480d173`). `COGA_LAUNCH_RETURNS_CHECKOUT=1`: handoff stays on the feature branch and launch returns the checkout after bump.

Baseline command (run from `/tmp/coga-discharge-main-a07e92h8`):
```sh
PYTHONPATH=/tmp/coga-discharge-main-a07e92h8/src /home/n/Code/claude/coga/.venv/bin/python -m pytest tests/test_packaging.py::test_live_and_packaged_copies_stay_identical tests/test_autoclose_sweep.py::test_autoclose_live_and_packaged_copies_stay_in_sync tests/test_upstream_coga.py::test_live_job_is_shaped_like_the_other_script_backed_jobs 'tests/test_compose.py::test_coga_repo_instructions_carry_the_minimal_core_boundary[CLAUDE.md]'
```
Result: 4 failed. These are the already-recorded live/packaged recurring drift and missing `CLAUDE.md`, outside this ticket's fixes.

## PR

```yaml
title: Discharge retires.md entries in the clone that owns them
author: claude/codex
author_evidence: Claude Code (claude-opus-5-5) implemented the original change; Codex independently reviewed it
  and authored the approved peer-review fixes in 87480d173.
head: 87480d173906855eeebfb1ab78d780429466a6a4
base: 1d89f9fbc688ab47729dbcc49026347a7c11e467
depth: deep
rationale: This adds checkout disposal in every clone and publication of a shared worklist from a clone-scoped job.
  Both review findings are fixed, but the fixes received self-review and the full suite has four independently reproduced
  baseline failures.
implementation: Branch sweep disposes of retire follow-ups whose recorded owner resolves to its repository, using
  the existing autoclose backlog walker and checkout proofs. It reconciles only those entries and publishes the
  worklist alone with an exact-byte CAS. Reconcile and publish share the local state lock; a failed or skipped publish
  restores the prior contents unless an intervening local writer changed them. Git-disabled and off-control invocations
  skip the follow-up pass.
deviations: Owner-approved review fixes make publication failure retryable and prevent a skipped publish being reported
  as discharge. Ownership still requires a recorded owner rather than inference, as explained in the implement handoff.
limitations: Ownerless entries remain autoclose-only. Pre-existing live recurring-template drift means this repository
  still needs its separate template repair before its own branch sweep runs clone-scoped. The four baseline test
  failures remain. Verification uses Python 3.12.12; the installed Python 3.11 lacks pytest. No interactive terminal
  or Slack rendering changed.
files:
  src/coga/retire_worklist.py: owned_here predicate; reconcile_worklist only= filter and WorklistChange.original.
  src/coga/autoclose.py: Factor the backlog walk into dispose_worklist_backlog with include/label.
  src/coga/branchsweep.py: Owned-entry disposal and scoped CAS publication, result/report fields, Git-enabled guard,
    and rollback that makes failed publication retryable without overwriting an intervening local edit.
  tests/test_retire_worklist.py: Cover owned_here and reconcile only=.
  tests/test_branchsweep.py: Integration coverage for disposal and publication, off-control and Git-disabled skips,
    transport/filesystem/skipped-publication recovery, concurrent local edits, and remote CAS refusal followed by
    a successful retry.
  docs/contexts/coga/recurring/scheduling/SKILL.md: State the pass and the one-commit exception for clone scope.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Packaged twin.
  docs/contexts/dev/checkout-cleanup/foreign-ownership/SKILL.md: The owning clone now settles its own entries.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/foreign-ownership/SKILL.md: Packaged
    twin.
  coga/skills/coga/autoclose/sweep/SKILL.md: Point the cross-clone section at the owning clone's pass.
  src/coga/resources/templates/coga/bootstrap/skills/coga/autoclose/sweep/SKILL.md: Packaged twin.
  coga/skills/coga/branch-sweep/sweep/SKILL.md: Describe the retire follow-up pass.
  src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: Template description step 7 and drop the no-commit
    claim.
  src/coga/recurring_clone.py: Align the module description with the documented template-owned publication exception;
    no runtime change.
  src/coga/recurring_runner.py: Align the clone-runner docstring with the publication exception; no runtime change.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 87480d173906855eeebfb1ab78d780429466a6a4
  base: 1d89f9fbc688ab47729dbcc49026347a7c11e467
  detail: Direct final review completed with no unresolved findings. Codex independently reviewed the Claude implementation
    at 36ce55db0682bb1fadf5590022452792ae05cb67, then authored and self-reviewed the approved recovery fixes. The
    complete final diff therefore is not claimed as independently reviewed.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest
  status: failed
  head: 87480d173906855eeebfb1ab78d780429466a6a4
  base: 1d89f9fbc688ab47729dbcc49026347a7c11e467
  detail: '3702 passed, 5 skipped, 4 failed on Python 3.12.12. All four failures were independently reproduced on
    main 1d89f9fbc: recurring-template twin drift (packaging/autoclose/upstream tests) and the missing CLAUDE.md
    compose check. The final run includes all eight follow-up publication and recovery cases, which passed.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 87480d173906855eeebfb1ab78d780429466a6a4
  base: 1d89f9fbc688ab47729dbcc49026347a7c11e467
  detail: No whitespace errors.
```
