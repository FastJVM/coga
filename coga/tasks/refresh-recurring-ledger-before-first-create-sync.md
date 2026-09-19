---
title: Refresh recurring ledger before first create sync
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
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
