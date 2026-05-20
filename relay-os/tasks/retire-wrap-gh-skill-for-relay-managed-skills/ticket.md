---
title: Retire wrap-gh-skill-for-relay-managed-skills
status: draft
mode: auto
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
---

## Description

Retire the done ticket `wrap-gh-skill-for-relay-managed-skills`.

Retire is the slug-targeted launcher for `retro/done-ticket`: extract durable
knowledge from one finished task and delete the source task directory in the
same PR. This task is the ad-hoc shell that drives that single skill against
the named slug. Do not invent additional steps. Branch hygiene (local prune,
stale-branch sweep) is a Dream concern, not retire's.

### Console Progress

Write short progress updates to the console before and after each phase: retro
PR open, final bump. Include the slug or PR link being acted on. The
blackboard remains the durable record; console progress is for the human
watching the run.

### Ordered Pass

Run these in order. Stop and ask if any precondition fails — do not improvise.

1. **Run `retro/done-ticket` against `wrap-gh-skill-for-relay-managed-skills`.** Read the skill at
   `relay-os/skills/retro/done-ticket/SKILL.md` and follow it. The skill
   stops and asks if the slug is ambiguous, the task is not `status: done`,
   or any required evidence file is missing. It opens a PR that records the
   `## Retro` marker, edits the knowledge base if warranted, and deletes
   `relay-os/tasks/wrap-gh-skill-for-relay-managed-skills/` in the same PR. Do not delete the directory
   outside the PR.

2. **Bump this retire task to done.** Run `relay bump <this-task-slug>`
   with a `--message` summarizing what happened: the retro PR link, or
   "no-op" if retro found no durable knowledge.

### Stop conditions

- Source task is not `status: done` → escalate via `relay panic` with the
  reason. Retire only operates on done tickets.
- Source task is missing → escalate; the slug is wrong.
- Retro skill stops and asks → surface the reason; do not improvise.
- Anything outside the allowed scope above → escalate, do not improvise.

## Context

