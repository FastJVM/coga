---
slug: agent-usage-report
title: agent-usage-report
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/usage
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

A recurring report that tells people where they stand with their AI usage, so
they can right-size their subscription. If someone on the $200 plan is only
using a quarter of it, the report should make that visible enough that
downgrading becomes an obvious call. Runs weekly or monthly — often enough to
act on, not so often it becomes noise.

## Context

Deliberately thin: this is the vision, not the design. The engineering path is
the `design` step's call — including the first question, which is that plan
utilization has **no defined denominator today**. Subscription plans are metered
by rate-limit windows, not a cumulative token allowance, so "a quarter of the
$200 plan" needs a proxy to be invented (API-equivalent cost via the price table
`coga/usage` defers, or something else). Deciding that is design work, not a
given.

Prior art and pointers:

- `coga usage` reads token records from `coga/log.md`; the attached `coga/usage`
  context describes that primitive and its deferred price table.
- `coga/recurring/digest/` is the closest model for a scheduled Slack report.
  Attach `coga/recurring` at design time if that shape is chosen — it's 54KB,
  too heavy to carry by default.
- `src/coga/recurring_autofix.py` (`_CLAUDE_SUBSCRIPTION_TYPES`, ~L105/L458) is
  the only place in the repo that knows which plan someone is on.

Two known gaps to caveat around, both **out of scope** here — fixing either is
its own ticket, so recommend a split rather than absorbing it:

- Usage records carry no `user` field. Attribution today is an approximate join
  through the record's `slug` to that ticket's `human:`/`owner:`; no schema
  change is needed or wanted for a first report.
- Only Coga-launched sessions are recorded, and only for this repo, so totals
  understate real usage — the direction of error that biases toward over-eager
  downgrade advice.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
