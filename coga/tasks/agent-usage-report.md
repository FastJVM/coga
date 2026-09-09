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

Deliberately thin: this is the vision, not the design. The engineering path —
how usage becomes a plan-utilization number, where the report lands, exact
cadence — is the `design` step's call.

`coga usage` already reads the token records out of `coga/log.md`; the attached
`coga/usage` context describes that primitive and explicitly defers a price
table as a follow-up. `coga/recurring/digest/` is the closest existing model
for a scheduled report that posts to Slack (attach `coga/recurring` at design
time if that shape is chosen — it's 54KB, too heavy to carry by default).

Two gaps the design should confront rather than inherit: usage records carry no
`user` field (`src/coga/usage.py:66-74`), so per-person numbers aren't derivable
today; and only Coga-launched sessions are recorded, so totals understate real
usage — which biases exactly toward over-eager downgrade advice.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
