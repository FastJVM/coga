---
name: coga/notifications/producers
description: The reviewed inventory of which Coga events post live, post as outcomes, or stay silent, with the module that actually calls post or notify for each.
---

# Notification producers

Which events reach the channel. Surfaces and destinations are defined in
[`coga/notifications`](../SKILL.md); failure handling in
[`coga/notifications/failures`](../failures/SKILL.md). The module named is
the one that calls `post(`/`notify(` — `commands/*` front-ends often only
preflight and hand a finished `slack_text` down — so grep for the real call
before adding a row.

## Live surface (`post`)

| Event | Caller | Destination |
| --- | --- | --- |
| `coga block` blocker, owner named | `mark.py` `mark_blocked` (`fatal=False`) | flow |
| Blocker reminder | `blocker_reminders.py` `remind_blocked_tasks` | flow |
| `coga slack` FYI | `commands/slack.py` | flow; important with `--important` |
| `coga bump --message` FYI | `bump.py` `advance_step` (`notify_slack=True`, `fatal=False`) | flow |
| `coga launch` of an `active` ticket (→ `in_progress`), once per task | `mark.py` `mark_in_progress` | flow |
| Recurring `ticket.py` exits non-zero | `launch_script.py` | important |
| Completed period failed to advance declared state | `mark.py` stale-period-state warning | important |
| Dream validate-drift summary | `dream_validate_drift.py` | flow |
| Megalaunch drain summary (non-empty) | `commands/megalaunch.py` | flow |
| Autoclose checkout summaries (disposed checkouts flow; refused disposals important) | `autoclose.py` `_report_retire_followups` (`fatal=False`) | flow / important |
| Autoclose unanswered review-thread summary on the PRs it closes (`coga/autoclose/sweep` skill) | `autoclose.py` `_report_followup` (`fatal=False`) | flow |
| `recurring/phone-home` weekly snapshot receipt ([job contract](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/ticket.md)) | `coga_edge/phone_home.py` `_receipt`, reached through the phone-home `ticket.py` shim (`fatal=False`, `record_failure=False`) | flow |
| Autofix filed a ticket for a problem run (failed, silently idle, or with recorded errors) | `recurring_autofix.py` `run_autofix` and `run_autofix_analyze_recipe` | flow |

Downstream reminder sweeps built on `src/coga/reminders.py` post their alerts
through the `coga slack` command, so they ride that row.

Relaunching an already-`in_progress` ticket does not post: the start
transition already happened.

## Outcome surface (`notify`)

| Event | Caller | Destination |
| --- | --- | --- |
| `coga mark done`, including manual completions with no PR and the `autoclose-merged` sweep's merged-PR closes | `mark.py` `mark_done` | flow |
| `coga mark canceled`, with its required reason | `mark.py` `mark_canceled` | flow |
| Template parse failures in a recurring scan | `recurring_runner._broadcast_scan` (`fatal=False`) | important |
| Recurring period contradiction: failed create sync leaves another ticket copy in place, so the period cannot run as created | `recurring_runner._flag_period_contradiction` (`kind="recurring-error"`, `fatal=False`) | important |
| Watchdog timeout pause | `mark.py` `mark_paused` when the watchdog supplies `slack_text` | important |
| Re-escalation of each already-watchdog-paused task on every later sweep, until it completes | `recurring_runner.run_recurring_scan` (`fatal=False`) | important |

`coga status` is read-only and never closes tickets; the daily autoclose sweep
is the sole automatic `done` trigger. Manual pauses and non-timeout pauses are
silent. Resume a watchdog-paused task with `coga launch <slug>`; its
successful completion stops the re-escalations.

## Silent

`coga create` and `coga ticket`; `mark active`; manual `mark paused`;
message-less `bump`; successful recurring creates; `coga retire`; the
branch-sweep template (`branchsweep.py` posts nothing and writes a
`## Branch Sweep` blackboard report, or stdout without a task); the
skill-update template (its PR is the notification); and the
`resolve-conflicts` and `address-pr-comments` templates, whose own period
tasks emit nothing while their bootstrap delegates post one roll-up through
`coga slack`.

## Accounting rule

This is an accounting of **event kinds, not templates**: one template may span
surfaces (`autoclose-merged` posts live checkout and review-thread summaries and per-ticket
outcomes). A new template or event kind that appears on none of the three
surfaces is an unreviewed cadence decision, not a neutral default. Keep this
inventory in step with `coga/recurring` when templates change.

The [blocker-reminders template](https://github.com/FastJVM/coga/blob/main/coga/recurring/blocker-reminders/ticket.md) owns reminder eligibility,
recovery guidance and its one-attempt watermark.
