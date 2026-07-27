---
slug: v2/coga-recurring-ack
title: coga recurring ack — CLI to record a reminder's ack
status: draft
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Add a `coga recurring ack <name>` command (and the matching `--ack` flag on the
reminder engine's `run()` harness) that records a reminder's ack — its "done for
this period" marker — by writing `Acked: <value>` to the named reminder's
ticket. Today the only way to ack is to call `record_ack()` in Python or
hand-edit the blackboard, which is not viable for monthly use.

## Context

- The reminder engine ships `read_ack` / `record_ack` but no human-facing verb;
  the engine ticket deferred this until admin's first ack reminder existed.
- That condition is now met: `xero-reconcile` and the franchise-tax reminders
  are ack-based, and their shapes are pinned — a period `Acked: YYYY-MM`, or a
  date high-water `Acked: YYYY-MM-DD`.
- The sweep owns what the ack value means, so the CLI records whatever the
  reminder's `period_for(today)` returns.
- Default: `coga recurring ack <name>` computes the current value from the
  reminder's `period_for(today)`; `--period <value>` overrides it, for acking a
  past period or setting a specific high-water date.
- Depends on the reminder engine landing. See the `coga/reminders` SKILL.
