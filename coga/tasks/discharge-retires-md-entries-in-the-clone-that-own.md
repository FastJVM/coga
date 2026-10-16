---
title: Discharge retires.md entries in the clone that owns them
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

Follow-up to run-clone-local-recurring-work-in-every-clone (owner decision 2026-10-16: kept out of that PR). Branch-sweep is now `scope: clone` and runs daily in every clone, but re-judging the autoclose-merged `retires.md` worklist still happens only in whichever clone services the repo-scoped autoclose-merged period. An entry whose `owner` is another clone (a foreign primary, or a foreign linked worktree) is reported for manual cleanup there and never discharges unless that clone happens to run autoclose. Wanted: a clone-scoped pass that judges and disposes of the entries owned by the sweeping clone, through the existing proofs in `checkout_disposal.dispose_checkout` and `retire_worklist`, and discharges them. Open design question: discharging edits `retires.md`, which is committed (`merge=union`, CAS-written). That breaks the 'clone scope commits nothing' property, so the pass needs its own publish path (for example `git.publish` of just that file, as upstream-coga does for its cursor). Related: autoclose-re-posts-another-clone-s-primary-checkou.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

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

## PR

```yaml
title: Discharge retires.md entries in the clone that owns them
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5); see implement handoff.
head: a1bfcc4ddaf1681f95d08fb4c74962a05f3f9ae7
base: 6cbf1e3cc9a149104ca2776182969365a66080a2
depth: deep
rationale: New destructive path (worktree/branch disposal) now runs in every clone, and a clone-scoped job gains a commit to control; no independent review yet.
implementation: Clone-scoped branch sweep disposes of and discharges retires.md entries whose recorded owner is its own repository, reusing autoclose's backlog walk and the retire proofs, reconciling only those entries, and publishing the worklist alone with a CAS expect.
deviations: None from the owner-approved plan, except owned_here uses only a recorded owner (no inference), since inference from the owning clone can never name itself.
limitations: Ownerless entries remain autoclose-only. Live coga/recurring templates in this repo are stale versus packaged (pre-existing), so the live branch-sweep here does not yet run clone-scoped.
files:
  src/coga/retire_worklist.py: owned_here predicate; reconcile_worklist only= filter and WorklistChange.original.
  src/coga/autoclose.py: Factor the backlog walk into dispose_worklist_backlog with include/label.
  src/coga/branchsweep.py: discharge_owned_followups phase, result fields, report lines.
  tests/test_retire_worklist.py: Cover owned_here and reconcile only=.
  tests/test_branchsweep.py: Cover owned-entry disposal plus publish, and the off-control skip.
  docs/contexts/coga/recurring/scheduling/SKILL.md: State the pass and the one-commit exception for clone scope.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Packaged twin.
  docs/contexts/dev/checkout-cleanup/foreign-ownership/SKILL.md: The owning clone now settles its own entries.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/foreign-ownership/SKILL.md: Packaged twin.
  coga/skills/coga/autoclose/sweep/SKILL.md: Point the cross-clone section at the owning clone's pass.
  src/coga/resources/templates/coga/bootstrap/skills/coga/autoclose/sweep/SKILL.md: Packaged twin.
  coga/skills/coga/branch-sweep/sweep/SKILL.md: Describe the retire follow-up pass.
  src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: Template description step 7 and drop the no-commit claim.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Code review belongs to the next workflow step (peer-review); design approval in chat is not code review.
checks:
  - command: python -m pytest tests/test_branchsweep.py tests/test_retire_worklist.py tests/test_autoclose_dispose.py tests/test_autoclose.py tests/test_retire.py
    status: passed
    head: a1bfcc4ddaf1681f95d08fb4c74962a05f3f9ae7
    base: 6cbf1e3cc9a149104ca2776182969365a66080a2
    detail: 361 passed (run on the uncommitted tree; committed src/tests/docs identical; the rebase brought only a ticket-file change).
  - command: python -m pytest
    status: failed
    head: a1bfcc4ddaf1681f95d08fb4c74962a05f3f9ae7
    base: 6cbf1e3cc9a149104ca2776182969365a66080a2
    detail: 3696 passed, 5 skipped, 4 failed; all 4 fail identically on origin/main without this change (live/packaged recurring template drift and CLAUDE.md compose check), see handoff.
```
