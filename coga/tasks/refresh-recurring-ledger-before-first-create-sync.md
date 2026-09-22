---
title: Refresh recurring ledger before first create sync
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

A normal recurring sweep can publish a period already completed and reaped by another checkout. Revalidate the control-ledger snapshot before the first create publication so the competing serviced record suppresses the duplicate task and launch, while preserving bounded ledger reads and serviceability of other due templates in the same sweep.

This P1 follow-up comes from [the triage](triage-five-review-comments-that-merged-unanswered.md). The owner approved this scope and draft on 2026-09-18; keep the ticket a draft until explicitly launched or activated.

## Context

### Evidence and source

Original [PR 699 comment](https://github.com/FastJVM/coga/pull/699#discussion_r3806973475); source ticket: [read-the-recurring-serviced-period-from-the-log-dr](read-the-recurring-serviced-period-from-the-log-dr.md). Assessed 2026-09-18 on control commit `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

A two-checkout local-Git probe caught up checkout A, scanned a due period, then pushed checkout B's serviced record with no remaining task before A's first create sync. With the normal preloaded cache, A republished the task and retained it in the launch list. With the cache not preloaded, the same scenario skipped it. This demonstrated duplicate publication and retained launch eligibility; duplicate dispatch was inferred, not observed. No production recurring run or agent dispatch was performed. Recheck this evidence against the implementation checkout before changing code.

### Expected behavior and scope

In `src/coga/recurring_runner.py`, `recurring_runner._broadcast_scan` preloads the pre-create ledger when pre-scan catch-up succeeded. `recurring_runner._sync_recurring_create_paths` and `recurring_runner._land_recurring_create_on_control_branch` fetch control and call `recurring_runner._control_already_has_period`, but `recurring_runner._control_serviced_period_cached` trusts the loaded snapshot despite the newer revision. `recurring_runner._validate_control_serviced_period` checks malformed data using that same snapshot; it is not a freshness repair.

Bind the pre-publication snapshot to the observed control revision and refresh or safely refuse when a newly observed revision invalidates it. Such a freshness refusal must be visible and exclude the affected task from dispatch; it must not fall through the generic `GitError` fallback in `recurring_runner._sync_recurring_create_paths` that preserves launch eligibility. This fix does not redesign unreachable-control behavior: preserve existing best-effort outer fetch/sync handling and the stricter per-child admission checks.

Preserve the shared-log self-collision protection: the first publication can carry pending records for other templates in this same sweep. Blindly refreshing on every template can suppress this sweep's own work. Retain the complete set of requested period targets, bounded local ledger reads when the relevant control revision is unchanged, malformed-ledger refusal, generation checks, and explicit forced/named rerun semantics. The log remains the dedup source and is union-merged across checkouts; do not add a persistent duplicate ledger.

Document the freshness boundary and what is guaranteed if control advances again during publication, including a non-fast-forward create-sync retry. Distinguish competing records from this sweep's own published records; do not claim global exactly-once execution.

### Acceptance and focused verification

- Reproduce the original interleaving using a local bare remote and two checkouts, with the normal preloaded cache. A competing completed/reaped period must not be recreated on control or dispatched. Compare the non-preloaded path as well.
- Include the equivalent case where the competing task still exists; preserve that task and exclude the losing local create from dispatch.
- Multiple due templates from one sweep must all remain serviceable without mistaking their own pending log records for competing work.
- If freshness refusal leaves a local task behind, a second same-period sweep must not dispatch a duplicate through the reused-task path that skips create-sync.
- Preserve unchanged-control bounded reads, malformed-ledger refusal, generation checks, and forced/named reruns. Exercise create-sync retry against a changed control revision and assert the documented refresh or refusal behavior.
- Extend `tests/test_recurring.py` around fresh pre-scan cache reuse, handled-period sync, control-ledger validation, and multi-template sweeps. Use mocked dispatch; no live recurring jobs.
- Update the dedup contract in `coga/contexts/coga/recurring/SKILL.md` and any affected `coga/current-direction` summary, plus the PR 699 gotcha in `coga/codebase`; keep each existing packaged context twin byte-identical and run packaging checks.

Useful regression anchors in `tests/test_recurring.py` are `test_broadcast_reuses_the_fresh_prescan_control_ledger`, `test_recurring_create_sync_restores_control_ledger_for_handled_period`, `test_recurring_sweep_skips_task_removed_by_create_sync`, `test_feature_branch_sweep_revalidates_malformed_control_ledger_on_retry`, and `test_control_ledger_landing_preserves_a_peer_append`. Run `python -m pytest tests/test_recurring.py tests/test_packaging.py`; the workflow also requires the full suite before PR handoff. Use an environment that imports this checkout's source.

### Focused context reads and documentation

The implementation and peer-review steps must read these sections, and the owner review must check that the resulting contract matches the tested guarantee. The open-pr step uses the resulting reviewed diff and test record; it needs no additional context attachment.

- `coga/recurring` (`coga/contexts/coga/recurring/SKILL.md`) is cited rather than attached: read "The creation contract," "Recurring runs start on the control branch," and the forced/named entry points under "A recurring task is a ticket-format directory." The high-water mark outlives a reaped task; the bounded reverse reader resolves all requested targets together, and the shared-log snapshot prevents self-collision. Update the snapshot wording to describe the new freshness boundary while preserving the distinct outer-fetch and per-child admission contracts.
- `coga/current-direction` (`coga/contexts/coga/current-direction/SKILL.md`) is cited rather than attached: read "Current redesign (recurring lifecycle and identity)." Keep its summary of stable task identity, log-based dedup, cleanup, and explicit overrides consistent with the owning recurring contract.
- `coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`) is cited rather than attached: read the PR 699 bullet under "Gotchas when editing coga's own code" and "Installed-versus-source skew warning." Update the historical defect note with the fix and its limit; verify using this checkout's source rather than a differently installed Coga tree.

The recurring and codebase packaged twins live at `src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md` and `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`. There is currently no packaged current-direction twin; update any twin that exists when implementing. Citing an editing target does not remove the same-PR documentation obligation.

### Tradeoff and exclusions

A revision/freshness check adds synchronization cost and must preserve attribution of locally pending ledger lines. Out of scope: new services, scheduler redesign, replies or resolution on historical PR 699/triage threads, and unrelated merge policy. Review feedback on the new fix PR follows the existing workflow; thread resolution and merge remain owner-controlled. Trimming shared workflow skills is separate process maintenance.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/838
branch: fix/recurring-ledger-freshness
worktree: /tmp/coga-recurring-ledger-freshness

## Implementation notes

- Owner confirmed the implementation plan in the attended session on 2026-09-18.
- Rechecked `recurring_runner._control_serviced_period_cached`: the preloaded
  cache has no revision binding; create and retry fetches reuse it unchanged.
- Implement in the separate feature checkout; preserve the primary checkout's
  pre-existing generated log edit. No push or PR in this step.
- Plan: bind pre-create cache to control revision, refresh all requested targets
  before first publication when it changes, and recognize this sweep's own
  published log. If a later external log change cannot be safely attributed,
  refuse visibly and clean up the local candidate so it cannot bypass admission
  on a second sweep. Keep unchanged-log reuse and existing transport behavior.
- Regression reproduced on the fresh feature checkout: the reaped/preloaded
  case republished the task; fallback and existing-peer cases passed. No live
  dispatch was used. The new tests also assert removal from `scan.due`.
- Implemented revision binding, complete-target refresh before first successful
  publication (including rejected-push retries), and tracking of known own
  publications. Afterwards, a Git log diff identifies externally changed
  template ledger lines; those templates refuse conservatively while unrelated
  templates remain serviceable. Explicit overrides still refresh/validate but
  bypass dedup comparisons.
- Tests run from `/tmp/coga-ledger-test-env` (editable feature install), with
  absolute `PYTHONPATH=/tmp/coga-recurring-ledger-freshness/src` to avoid source
  skew. Initial recurring suite: 374 passed, 2 failures caused by skip-reason
  ordering; preserving the generation-change check before handled-period skip
  fixed both. Expanded race/retry/refusal and full verification results follow.
- Focused verification passed: `PYTHONPATH=/tmp/coga-recurring-ledger-freshness/src
  /tmp/coga-ledger-test-env/bin/python -m pytest tests/test_recurring.py
  tests/test_packaging.py -q` — **402 passed**. Includes preloaded/fallback,
  reaped/done/active peer, initial and post-publication push retries on both
  control and feature branches, full-target cache reuse, unaffected templates,
  second-sweep suppression after refusal, read failures, and forced validation.
- Updated the owning recurring contract, current-direction pointer, and PR 699
  codebase gotcha; copied both existing packaged twins. No task-layout, prompt,
  or workflow-schema change, so no example fixture change is required.
- Guarantee limit: before any own publication, refreshed control suppresses a
  competitor's serviced period. Afterwards, only observable changed ledger
  lines can be attributed conservatively; byte-identical competing records or
  changes with no net diff cannot be distinguished. This is not exactly-once
  execution. Existing outer transport fallback and per-child leases remain.
- Full verification passed: `PYTHONPATH=/tmp/coga-recurring-ledger-freshness/src
  /tmp/coga-ledger-test-env/bin/python -m pytest` — **2674 passed in 200.39s**.
- Committed as `632942a8` (`Refresh recurring ledger before create publication`)
  after fetching and rebasing onto `origin/main` at `4425d829`. Upstream changed
  only another ticket and `coga/log.md`; implementation/source/test/context
  bytes are unchanged by the rebase. Post-rebase focused rerun: **402 passed in
  53.10s** using the exact focused command above. `git diff --check` passed and
  `git merge-base --is-ancestor origin/main HEAD` confirmed freshness. Feature
  checkout is clean. No implementation push or PR.

## Implement handoff

Implementation complete; ready for peer review. The reviewed guarantee should
match the owning recurring context's observed-revision boundary, especially
conservative post-publication refusal and byte-identical/net-zero-diff limits.
All tests use local Git remotes and mocked dispatch; no live recurring jobs ran.


## Peer review

- `codex review --base main` **returned** (exit 0) on 2026-09-18.
  Review transcript: `/tmp/coga-ledger-peer-review.log` (local artifact).
- One must-fix P2: a transient first create-fetch failure followed by a
  successful `git.sync_paths` fallback publishes pending sweep ledger records
  without updating the cache's own-publication provenance. The next template
  refreshes and mistakes its own pending record for a competitor, suppressing
  its work. The reviewer reproduced this with two templates; only the first
  remained due. The existing recurring suite passed (389 tests).
- Owner approved the fallback-provenance fix in this attended session.
- Generic path sync now returns the accepted control revision for ordinary
  publication. The recurring fallback uses its existing guard for ledger
  admission/retry checks and records that exact revision as its own publication.
  A subsequent fetch cannot accidentally attribute an intervening peer push to
  this sweep. Transport failures still save the local create and remain
  best-effort; ledger refusals do not enter that fallback.
- Added 16 local-Git cases covering control/feature branches, cold/preloaded
  caches, and no competitor or a competitor before/during/after fallback
  publication. With existing fallback cases, 20 targeted tests passed.
- Focused verification initially exposed the existing offline local-commit
  contract (417 passed, 1 failed); restored local commit after a non-publishing
  generic fallback; the final verification below passes that regression.
- No raw-terminal, pager, TTY prompt, or rendered Slack surface changed; this
  diff changes recurring admission and plain console skip diagnostics.
- Follow-up `codex review --base main` **returned** (exit 0), with one
  additional P2 in the same provenance boundary: after a first create loses
  its push retry, the subsequent audit-only push publishes pending records
  without marking them as this sweep's own. Transcript:
  `/tmp/coga-ledger-peer-review-followup.log` (local artifact).
- Fixed both returned findings. Generic fallback publications return their
  accepted control OID and guard ledger admission/retries; audit-only pushes
  bind the cache to pushed HEAD and refresh the competitor snapshot on retry.
  Added four audit-publication cases alongside the sixteen fallback cases.
  All 25 targeted tests passed, including existing transport/offline contracts.
- Committed the fixes, then rebased unconditionally onto fetched main at
  `460ea14c`. Feature HEAD is `df6ed6cb` (implementation `96ada5de`). Rebase
  brought only an unrelated ticket update; feature checkout is clean and
  `git diff origin/main...HEAD --check` passes. Both returned findings are
  addressed, and the PR description is authored below.
- Final post-rebase verification, importing this checkout's source explicitly
  under Python 3.12.12:
  - `PYTHONPATH=/tmp/coga-recurring-ledger-freshness/src /tmp/coga-ledger-test-env/bin/python -m pytest tests/test_recurring.py tests/test_packaging.py -q`
    — **422 passed in 63.65s**.
  - `PYTHONPATH=/tmp/coga-recurring-ledger-freshness/src /tmp/coga-ledger-test-env/bin/python -m pytest`
    — **2694 passed in 207.95s**.
- Feature branch is clean, committed, and ahead of fetched main; no feature
  push or PR was performed in peer review. Ready for the mechanical open-pr
  step. The primary checkout's existing generated log changes were preserved.

## Open PR

- Confirmed the `## Peer review` note records both `codex review` runs as
  returned with findings fixed; no review in flight. Feature checkout was clean
  at `df6ed6cb`, two commits ahead; `origin/main` had advanced only through
  generated task/log lifecycle commits.
- `coga open-pr` ran from the primary control checkout on 2026-09-18 and
  opened PR #838 (`fix/recurring-ledger-freshness` -> `main`, non-draft).
  `pr:` recorded under `## Dev`. Merge is owner-controlled in the next step.

## PR

A competing checkout can finish and reap a recurring period after the sweep
scans it but before its first create sync. Bind the pre-create ledger cache to
control's revision and refresh every requested target before publication and
on rejected-push retries, so the losing create is excluded from dispatch.

Track this sweep's own publications, including recovered generic sync and
log-only pushes, so pending records do not suppress other due templates.
Refuse ambiguous later ledger changes visibly and discard local candidates
that could bypass admission on the next sweep. Preserve explicit reruns,
malformed-ledger checks, offline local saves, and bounded unchanged-revision
reads. Update the recurring contract, current-direction summary, and codebase
gotcha, with packaged context twins kept identical.

The guarantee is tied to observed control revisions: byte-identical competing
records and intervening changes with no net ledger diff are not distinguishable;
this does not provide global exactly-once execution.

Test plan: `PYTHONPATH=/tmp/coga-recurring-ledger-freshness/src /tmp/coga-ledger-test-env/bin/python -m pytest tests/test_recurring.py tests/test_packaging.py -q` (422 passed); `PYTHONPATH=/tmp/coga-recurring-ledger-freshness/src /tmp/coga-ledger-test-env/bin/python -m pytest` (2694 passed). Local Git remotes and mocked dispatch only; no live recurring jobs.
