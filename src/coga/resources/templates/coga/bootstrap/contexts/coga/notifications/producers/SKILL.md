---
name: coga/notifications/producers
description: The reviewed inventory of which Coga events post live, post as outcomes, or stay silent, and the destination each one uses.
---

# Notification producers

Which events reach the channel. Surfaces and destinations, and what happens
when a post fails, are defined in [`coga/notifications`](../SKILL.md).

## Live surface

| Event | Destination |
| --- | --- |
| `coga block` blocker, owner named | flow |
| Blocker reminder | flow |
| `coga slack` FYI | flow; important with `--important` |
| `coga bump --message` FYI | flow |
| `coga launch` of an `active` ticket (→ `in_progress`), once per task | flow |
| Recurring `ticket.py` exits non-zero | important |
| Completed period failed to advance declared state | important |
| Dream validate-drift summary | flow |
| Megalaunch drain summary (non-empty) | flow |
| Autoclose checkout summaries (disposed checkouts flow; refused disposals important) | flow / important |
| Autoclose unanswered review-thread summary on the PRs it closes (`coga/autoclose/sweep` skill) | flow |
| `recurring/phone-home` weekly snapshot receipt ([job contract](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/ticket.md)); a delivery miss stays off `coga/log.md` | flow |
| Autofix filed a ticket for a problem run (failed, silently idle, or with recorded errors) | flow |

Downstream reminder sweeps built on `src/coga/reminders.py` post their alerts
through the `coga slack` command, so they ride that row.

Relaunching an already-`in_progress` ticket does not post: the start
transition already happened.

## Outcome surface

| Event | Destination |
| --- | --- |
| `coga mark done`, including manual completions with no PR and the `autoclose-merged` sweep's merged-PR closes | flow |
| `coga mark canceled`, with its required reason | flow |
| Template parse failures in a recurring scan | important |
| Recurring period contradiction: failed create sync leaves another ticket copy in place, so the period cannot run as created | important |
| Watchdog timeout pause | important |
| Re-escalation of each already-watchdog-paused task on every later sweep, until it completes | important |

`coga status` is read-only and never closes tickets; the daily autoclose sweep
is the sole automatic `done` trigger. Manual pauses and non-timeout pauses are
silent. Resume a watchdog-paused task with `coga launch <slug>`; its
successful completion stops the re-escalations.

## Silent

`coga create` and `coga ticket`; `mark active`; manual `mark paused`;
message-less `bump`; successful recurring creates; `coga retire`; the
branch-sweep template (it writes a `## Branch Sweep` blackboard report, or
stdout without a task); the skill-update template (its PR is the
notification); and the `resolve-conflicts` and `address-pr-comments`
templates, whose own period tasks emit nothing while their bootstrap
delegates post one roll-up through `coga slack`.

The [blocker-reminders template](https://github.com/FastJVM/coga/blob/main/coga/recurring/blocker-reminders/ticket.md) owns reminder eligibility,
recovery guidance and its one-attempt watermark.
