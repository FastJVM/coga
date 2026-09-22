---
title: Agent usage report
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 5f3061a4-f3cd-42ab-921a-5dfe010d65ca
workflow:
  name: usage-report/post
  steps:
  - name: post
    skills:
    - coga/usage-report/post
    assignee: agent
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
3. posts that text once through `coga.notification.post` with
   `important=True, fatal=False` — a delivery miss is reported and the period
   still closes — and completes its own step with `coga bump`.

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
