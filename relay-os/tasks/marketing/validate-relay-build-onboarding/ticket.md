---
title: Validate relay build onboarding
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
---

## Description

Test the `relay build` onboarding flow end to end — the single scripted
question ("what do you want to build?") → agent-led chat → scan → spec → first
batch of draft tickets — across the repo states it has to handle. The win
condition is the same each time: the user finishes with a batch of tickets they
can immediately `relay launch`, and the batch is not fact-thin. Human-driven
(workflow-less): run it only once the flow ships (`marketing/relay-build-onboarding-flow`
+ `marketing/remove-relay-setup-command`).

## Context

- Scenarios (reuse the `init-questions` fixtures where possible —
  `~/Desktop/admin-init-test` and `~/Desktop/admin-fresh`):
  1. **Empty repo** — no code, no CLAUDE.md. Exercises the intent-only path
     (scan finds nothing); check the starter batch isn't fact-thin.
  2. **Filled repo, no CLAUDE.md** — real code/README/config. Check the scan
     recovers operation the single question can't (per init-questions:
     answers-only ≈ 7/20 facts, scan ≈ 20/20).
  3. **Filled repo, with CLAUDE.md** — check the scan ingests the existing
     agent guide and the generated tickets/spec don't duplicate or ignore it.
  - (A 4th — empty repo whose only file is a CLAUDE.md — is folded into #1
     unless it proves worth isolating.)
- Compare against the recorded ground truth from the `init-questions` dry-run
  eval (scorecard + Zach's verbatim answers are on that ticket's blackboard) so
  the recall numbers are measured, not eyeballed.
- This validates behavior, not code structure — it has no workflow on purpose;
  `relay mark done` it when the runs pass.
