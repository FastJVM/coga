---
title: Agent usage report
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: b6fcc8ad-a22d-4c45-8723-6126059e026f
workflow:
  name: usage-report/post
  steps:
  - name: post
    skills:
    - coga/usage-report/post
    assignee: agent
step: 1 (post)
---

## Description

Post one Slack message saying how many tokens this repo's Coga-launched agent
sessions consumed last week.

Coga records every launched session's usage into `coga/log.md` and reads it
back with `coga usage`, but nobody looks unless they ask. This task pushes the
number weekly, to the **important** route, so consumption is visible on a
cadence short enough to notice a change.

Once a week this recurring task's `ticket.py` runs `report.py` beside it,
which:

1. takes the last completed ISO week — previous Monday 00:00 to this Monday
   00:00, a half-open `[since, until)` window in UTC — and rolls the usage
   records in `coga/log.md` up over it with `coga.usage.rollup`,
2. renders total tokens and session count, the four token categories, a
   per-model split in which `(unknown)` and `<synthetic>` are rows of their
   own, and the count of `usage_status: unknown` sessions stated as a floor,
3. reads the generated period ticket's owner (falling back to
   `cfg.current_user` when absent) and passes it to `coga.notification.post`
   with `important=True, fatal=False`. The shared
   [notification prefix](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/notifications/SKILL.md#pinging-the-owner)
   identifies the reporting repo and pings a mapped owner; an unmapped owner
   keeps the plain-name fallback. It posts once — a delivery miss is reported
   and the period still closes — and completes its own step with `coga bump`.

The report is a pure function of `coga/log.md` and the window, so it keeps no
cursor and declares no `state_keys:`. A missed or lost week is recovered by
rendering it ad hoc and reposting by hand:

    python coga/recurring/usage-report/report.py --since 2026-08-31 --until 2026-09-07
    coga slack --task <slug> --message "$(python coga/recurring/usage-report/report.py --since … --until …)"

It reports token counts only: no dollar figures, no plan comparison, no
per-person attribution.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
