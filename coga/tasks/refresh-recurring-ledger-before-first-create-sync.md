---
title: Refresh recurring ledger before first create sync
status: draft
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
---

## Description

A normal recurring sweep can publish a period already completed and reaped by another checkout. Revalidate the control-ledger snapshot before the first create publication so the competing serviced record suppresses the duplicate task and launch.

This is a provisional P1 fix scope from [the triage](triage-five-review-comments-that-merged-unanswered.md). Owner: nicktoper; verdict not yet set. Keep this ticket a draft until the owner accepts or revises the scope.

### Evidence and source

Original [PR 699 comment](https://github.com/FastJVM/coga/pull/699#discussion_r3806973475); source ticket: [read-the-recurring-serviced-period-from-the-log-dr](read-the-recurring-serviced-period-from-the-log-dr.md). Assessed 2026-09-18 on control commit `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

A two-checkout local-Git probe caught up checkout A, scanned a due period, then pushed checkout B's serviced record with no remaining task before A's first create sync. With the normal preloaded cache, A republished the task and retained it in the launch list. With the cache not preloaded, the same scenario skipped it. No production recurring run or agent dispatch was performed.

### Expected behavior and scope

Follow `recurring_runner._broadcast_scan`, `_sync_recurring_create_paths`, `_land_recurring_create_on_control_branch`, `_control_already_has_period`, `_control_serviced_period_cached`, and `_validate_control_serviced_period` in `src/coga/recurring_runner.py`. The last function validates malformed data but trusts a loaded snapshot; it does not repair freshness.

Bind the pre-publication snapshot to the observed control revision and refresh or safely refuse when a newer revision invalidates it. Preserve the shared-log self-collision protection: the first publication can carry pending records for other templates in this same sweep. Blindly refreshing on every template can suppress this sweep's own work. Retain bounded local ledger reads when the relevant control revision is unchanged, malformed-ledger refusal, generation checks, and explicit forced/named rerun semantics. Document what is guaranteed if control advances again during publication; do not claim global exactly-once execution.

### Acceptance and focused verification

- Reproduce the original interleaving using a local bare remote and two checkouts. A competing completed/reaped period must not be recreated or dispatched.
- Include the equivalent case where the competing task still exists.
- Multiple due templates from one sweep must all remain serviceable without mistaking their own pending log records for competing work.
- Preserve unchanged-control bounded reads, malformed-ledger refusal, and forced/named reruns. Exercise create-sync retry where relevant.
- Extend `tests/test_recurring.py` around fresh pre-scan cache reuse, handled-period sync, control-ledger validation, and multi-template sweeps. Use mocked dispatch; no live recurring jobs.
- Update the dedup contract in `coga/contexts/coga/recurring/SKILL.md` and any affected `coga/current-direction` summary, plus the PR 699 gotcha in `coga/codebase`; keep each packaged context twin byte-identical and run packaging checks.

Tradeoff: a revision/freshness check adds synchronization cost and must preserve attribution of locally pending ledger lines. Out of scope: new services, scheduler redesign, review-thread replies/resolution, and unrelated merge policy.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
