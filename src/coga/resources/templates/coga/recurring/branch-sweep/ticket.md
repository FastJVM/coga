---
schedule: "0 7 * * 1"
schedule_comment: "Every Monday at 7am - prune stale git branches before the day's other automation starts"
title: "Branch sweep"
# The reserved `ticket.py` sibling is this task's deterministic half: `coga
# launch` runs it directly, with no agent and no composed prompt. The one-step
# workflow keeps the period task's lifecycle and skill contract legible.
workflow: branch-sweep/sweep
---

## Description

Archive and clean eligible local and remote feature branches, including
branches explicitly owned by done/canceled tickets whose PRs were deliberately
closed. Closed PRs alone never authorize deletion. Preserve live claims,
open PRs, unreviewed source changes, and unsafe checkouts; report every
refusal for inspection and retry.

The deterministic `ticket.py` runs `coga run branch-sweep`. Follow the
[coga/branch-sweep/sweep](skill:coga/branch-sweep/sweep) skill and the owning
[checkout cleanup contract](context:dev/checkout-cleanup). Cadence and the
daily autoclose composition belong to
[coga/recurring/scheduling](context:coga/recurring/scheduling).

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. The
`branch-sweep` sweep keeps no durable state here — every run's
output is the branches it deletes or reports as skipped, written as a
`## Branch Sweep` section on the period task's own blackboard. `coga
recurring` keeps the serviced-period record in the repo-global `coga/log.md`
(weekly period key `YYYY-Www`) once the first run has fired.
