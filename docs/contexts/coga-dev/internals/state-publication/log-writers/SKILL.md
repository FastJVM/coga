---
name: coga-dev/internals/state-publication/log-writers
description: Direct append_log writers and their publication owners, including ordinary startup grouping and every retained-state exit before a later publisher.
---

# Audit writers and publication owners

Part of [state publication](../SKILL.md). The user contract is
[every log line has a publisher](../../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md#every-log-line-has-a-publisher).
Re-inventory direct `append_log` calls under all of `src/`, including nested
functions, when changing a writer. Atomic appends and the local lock do not
replace the [event-aware publisher](../../spool-merge/SKILL.md).

The startup-group implementation inventory has **35 direct call sites**.
Counts below include repeated calls in one symbol. Paths are relative to
`src/`; names after `::` are symbols, not line numbers.

| Writer (sites) | Publisher and retained-state exits |
| --- | --- |
| `coga/launch.py::_LaunchInvocation._publish_startup` (3) | Activation, start, launch audit append under the state lock; the same finalizer calls `git.publish` for the ticket and required log before switch/spawn. Preflight exits write no lines. Any exception/interrupt after writes begin retains evidence and withholds return/sweep. A refused/failed/skipped/uncertain publish or failed confirmation starts no agent and reports the retained state. No transition is replayed as a retry. |
| `coga/launch.py::_LaunchInvocation._prepare_step_checkout` (1) | Non-grouped managed paths retain immediate `sync_log` before confirmation/switch. A planning/composition refusal precedes the append. Failed confirmation/entry retains state, reports, and withholds return/sweep. |
| `coga/launch.py::spawn_agent_session.record_and_publish_launch_audit` (1) | `commit_log=True` publishes immediately before execution for bootstrap, authoring, and other ordinary non-grouped callers. Megalaunch's deferred audit publishes in post-release admission; pre-release refusal retracts only its owned append, post-release failure keeps the audit and `released:` evidence. Guarded recurring callers retain their own publication boundary. Ordinary grouped spawn sets `record_launch=False`. |
| `coga_edge/megalaunch.py::_publish_partial_dependency_resolution` (1) | Appends under `git.state_lock` after rewriting the blocked ticket's blackboard, then publishes ticket and log together through strict `git.sync_task_state` with `expect` on the source ticket bytes. A definitely refused publish restores the ticket bytes and retracts the appended line when the local ticket is unchanged; an uncertain publish, or a refusal after the ticket changed locally, retains state for reconciliation and reports a failed result. |
| `coga_edge/megalaunch.py::_restore_after_failed_start` (1) | Appends under the state lock after restoring pre-launch ticket state. With Git enabled, strict `git.sync_task_state` publishes ticket and log against the launch claim. A definite failure attempts an owned rollback to the claim and retracts its append. Uncertainty retains the local restore for reconciliation. The result stops the megalaunch run. |
| `coga/mark.py::{mark_active,mark_in_progress,mark_done,mark_canceled,mark_blocked,mark_paused}`; `coga/bump.py::advance_step` (7) | Existing lifecycle task-plus-log publication; ordinary commands still publish promptly. Their strict callers retain the documented rollback versus uncertainty distinction. Grouped launch prepares activation/start without calling these durable wrappers; no default publication behavior changes. |
| `coga/commands/owner.py::owner`; `coga/commands/unblock.py::_apply_unblock` (3) | Existing task-plus-log publication, including unblock's separately attributed resolution and activation. |
| `coga/create.py::create_task`; `coga/commands/init.py::_do_init` (2) | Creation's caller publishes; init commits the scaffold and leaves its first push to the human. |
| `coga_edge/slack.py::slack` (1) | Script-phase line: rides the bootstrap launch's settlement or command-exit sweep; failed delivery is reported rather than retried recursively. |
| `coga/commands/mark.py::_finish_stateless_command` (1) | Explicit `sync_log`; the done marker waits for confirmation, a miss retains the line, withholds the sweep and exits 75. |
| `coga/launch_script.py::run_script_phase` (2) | Script start publishes before user code; exit rides strict-assist result publication, checkout settlement, or CLI sweep. Retained-state exits withhold the sweep and report the exit line. |
| `coga/recurring.py::{create_template,_record_run}`; `bootstrap/recurring-promote/promotion.py::promote_task`; `coga/recurring_runner.py::_append_forced_reused_log` (4) | Existing creation/adoption transaction, result/serviced-period ledger publisher, or command sweep. No ordinary-startup deferral. |
| `coga/recurring_runner.py::_run_delegated_task.start_period` (1) | Explicit delegated launch-log publication under period lease checks before child execution. |
| `coga/usage.py::append_record` (1) | `spawn_agent_session` captures usage in `finally`, then attempts log-only `sync_log`. Natural, failed, timed-out and interrupted sessions retain the child result; a failed/skipped publish adds the session-end retained-log warning. A spawn never admitted produces no usage record. Uncatchable death instead relies on next-entry recovery. |
| `coga/git.py::{record_sync_failure,_guard,refresh}`; `coga/notification/slack.py::SlackChannel.send.fail`; `coga/recurring_runner.py::_append_sync_failure`; `coga_edge/phone_home.py::run_phone_home` (6) | The failed operation's report covers these failure records. They do not start a recursive publication retry. A later eligible publication may carry them. |

## Notification and teardown after grouped startup

The successful-start notification follows checkout entry. On delivery failure,
`SlackChannel.send.fail` appends and reports its own line without making launch
fatal or invalidating a switch's cleanliness precondition. If a child starts,
the next lifecycle publication or usage teardown can carry it. If spawn fails
before usage, checkout return or the outer CLI sweep carries it. A refused
return/sweep retains and reports the line instead. This is not a fourth
publication in the successful-delivery workload.

After a child ends, usage publication remains log-only. It never broadens into
a root sweep and never delays the child's bump/mark/block handoff. Existing
settlement and CLI sweeps publish other eligible dirt, or explicitly report
and retain it when withheld. No cleanup claim covers uncatchable process death.
