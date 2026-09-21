---
title: Address PR review comments
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
delegate: bootstrap/address-pr-comments
period_generation: d84cfbe7-c8b2-4701-b71e-6d71d9468855
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
step: 1 (execute)
---

## Description

Run the stateless `coga address-pr-comments` command once a day, so review
comments on open PRs are addressed within a day of the next attended sweep
instead of waiting for someone to launch one ticket's `review` step by hand.

This recurring entry owns only the schedule. The command ticket under
`bootstrap/address-pr-comments` owns the operation: enumerate open PRs
targeting `main`, read each one's unresolved inline threads and unanswered
top-level comments from any author, apply the requested fixes on the PR
branch, verify, push under an exact lease, reply on the thread with the
marker that keeps the next day's sweep from answering itself, print one line
per PR, and post the final Slack roll-up. It never merges, never resolves a
thread, and never advances the PR's owning ticket; the human still owns the
review gate.

The `delegate:` field above is the whole delegation. Creation freezes it into
the period ticket, so sweeps, named retries, and direct
`coga launch recurring/address-pr-comments` never consult mutable template
dispatch. The runner marks the period task `in_progress`, launches
`bootstrap/address-pr-comments` in-process (honouring the sweep's `--agent`
override and selected queue session conduct), and marks the period task
`done` only after the delegated command's final `coga slack` roll-up emits
its bootstrap done sentinel. Everything else about how a delegated period is
preflighted, leased, published, timed out, and left retryable is the
`delegate` contract in the `coga/recurring` context, shared with
`recurring/resolve-conflicts`.

Because the delegated run is an agent launch, a cron-driven headless
`coga recurring` skips this template with a warning. It runs under an attended
sweep or an explicit `coga recurring launch address-pr-comments`, and every
attended sweep on a new day opens one agent session that inspects every open
PR. That cost was accepted when the template was authored. This template
intentionally covers **open PRs only**; rebasing a conflicting PR stays with
`resolve-conflicts`. For an on-demand run, or to scope one PR, call
`coga address-pr-comments [PR]` directly instead of forcing this recurring
template.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
