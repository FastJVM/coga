---
slug: retire-coga-important-support-second-webhook
title: Retire coga-important/support-second-webhook
status: in_progress
owner: zach
human: zach
agent: codex
assignee: codex
contexts: []
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
step: 1 (execute)
---

## Description

Retire the done ticket `coga-important/support-second-webhook`.

Retire is the slug-targeted launcher for `retro/done-ticket`: extract durable
knowledge from one finished task, then delete it. When new durable knowledge
exists, Retro opens a PR that records the `## Retro` marker, edits the knowledge
base, and deletes the source task directory in the same PR. When no new durable
knowledge exists, there is no PR to bundle the deletion into, so Retro
direct-deletes the task via `coga delete` — no marker, no PR. This task is the
ad-hoc shell that drives that single skill against the named slug. Do not
invent additional steps. Branch hygiene (local prune, stale-branch sweep) is a
Dream concern, not retire's.

### Console Progress

Write short progress updates to the console before and after each phase: retro
result, PR open when applicable, final status mark. Include the slug or PR link
being acted on. The blackboard remains the durable record; console progress is
for the human watching the run.

### Ordered Pass

Run these in order. Stop and ask if any precondition fails — do not improvise.

1. **Run `retro/done-ticket` against `coga-important/support-second-webhook`.** Read the skill at
   package `bootstrap/skills/retro/done-ticket/SKILL.md` unless a local
   `coga/skills/retro/done-ticket/SKILL.md` override exists, and follow it.
   The skill stops and asks if the slug is ambiguous, the task is not `status: done`,
   or any required evidence file is missing. When new durable knowledge exists,
   it opens a PR that records the `## Retro` marker, edits the knowledge base,
   and deletes `coga/tasks/coga-important/support-second-webhook/` in the same PR. When no new durable
   knowledge exists, it direct-deletes `coga/tasks/coga-important/support-second-webhook/` via
   `coga delete` — a working-tree `git rm` plus a direct
   `Ticket: coga-important/support-second-webhook — deleted` commit, with no PR and no marker. Recovery is via
   `git restore`.

2. **Mark this retire task done.** Run `coga mark done <this-task-slug>`
   with a `--message` summarizing what happened: the retro PR link, or
   "direct-deleted, no durable knowledge" when retro found nothing durable.

### Stop conditions

- Source task is not `status: done` → escalate via `coga block` with the
  reason. Retire only operates on done tickets.
- Source task is missing → escalate; the slug is wrong.
- Retro skill stops and asks → surface the reason; do not improvise.
- Anything outside the allowed scope above → escalate, do not improvise.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Findings

- 2026-08-13: Retro preflight stopped before delegation because the exact source task `coga-important/support-second-webhook` is absent from `coga/tasks/` on the current `main` checkout.
- Current history contains commit `bc94a150` (`Ticket: coga-important/support-second-webhook — deleted`), while `coga/log.md` shows this retire shell was created and first launched immediately after the source was marked done on 2026-07-16. The shell remained `in_progress` after the source deletion.
- Per this ticket's explicit missing-source stop condition, did not infer that the prior deletion completed this run, did not run Retro, and did not mark the retire shell done. Owner reconciliation is required: close/cancel this shell as already satisfied, or restore the source if Retro must be rerun.

---

## Blockers

- [ ] [2026-08-13 11:06] [agent:codex] id=20260813T110630 Source task coga-important/support-second-webhook is missing from the current control checkout; commit bc94a150 says it was already direct-deleted while this retire shell remained in_progress. Please decide whether to close/cancel this shell as already satisfied or restore the source for a fresh Retro run.
