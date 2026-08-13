---
slug: reconcile-recurring-wrapper-tty-admission-guidance
title: Reconcile recurring wrapper TTY-admission guidance with resolve-conflicts template
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

Dream 2026-W33 stale finding (F5): `coga/contexts/coga/recurring/SKILL.md` (Gotchas, ~lines 371-387) and the `coga/recurring/resolve-conflicts/ticket.md` template contradict each other on TTY admission for the delegated agent-backed sweep, and the contradiction broke a live run.

- The context tells the wrapper agent to run the delegated command under a fake pty (`timeout 900 script -qec 'coga resolve-conflicts --agent claude' /dev/null`) and confirm success via `coga/log.md`.
- The template says the opposite: "Recurring's outer agent supervisor remains responsible for TTY admission."
- The 2026-W33 resolve-conflicts run followed the template's framing, verified its tool shell has no TTY, judged the pty workaround a design bypass, and terminally blocked (blocker `20260813T094004`); the delegated sweep never ran.

One of the two must win: either the context's pty recipe is the sanctioned pattern (then the template should say so), or the wrapper shape is wrong and the template needs restructuring so the supervisor performs the delegated launch itself. The blocked run's blackboard leans structural. Decide the design, then fix whichever document (and possibly the template's step structure) loses — live and packaged copies both, if a packaged twin exists.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
