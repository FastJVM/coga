---
slug: check-we-can-extend-coga-recurring
title: check we can extend coga recurring
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/recurring
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Answer, then fix, one question: **can Coga's recurring system drive one of
our own task-specific tickets/workflows, or is it effectively locked to the
built-in template shape?**

First investigate the recurring engine and confirm what a recurring template
can and cannot carry — in particular whether a template can point at an
arbitrary `workflow:` and set of `contexts:` so a normal, task-specific ticket
(not just Dream / the bundled janitors) fires on a schedule. Then **close the
gaps** that block that: ship whatever documentation and/or code changes are
needed so a task-specific recurring ticket works cleanly, and fold the durable
"here's how you extend recurring with your own ticket" answer into the
`coga/recurring` context so it's captured for everyone.

Done looks like: a clear yes/no (with the real constraints named) is
documented in `coga/recurring`, and any concrete gap found during the
investigation is fixed in the same PR (or, if a gap is genuinely a separate
piece of work, spun out as a follow-up ticket and named in the PR).

## Context

The recurring subsystem already exists and is well-developed — this is an
"extend/verify", not a "build from scratch". Start here:

- **Context to read first:** `coga/recurring` (attached) — defines a recurring
  task as a ticket-format directory `coga/recurring/<name>/ticket.md` with a
  cron `schedule`, whose frontmatter *already* passes `workflow`, `contexts`,
  `owner`, `assignee`, `watchers` through to the created period task. That
  passthrough is the crux of the question: on paper a template can name any
  workflow, so the answer is likely "substantially yes, with constraints" —
  the job is to prove it and pin the constraints.
- **Code:** `src/coga/recurring.py`, `src/coga/recurring_runner.py`,
  `src/coga/commands/recurring.py`, `src/coga/period_state.py`. The scan +
  get-or-create + launch path is where any real limit will live (fixed period
  task path `coga/tasks/recurring/<name>/`, blackboard not carrying across
  runs except in the template, script-vs-agent deduction, one-step-workflow
  rules for script-backed templates).
- **Related patterns:** the spool/consumer pattern in
  `coga/contexts/coga/patterns/SKILL.md` and the per-firing rules in
  `coga/contexts/coga/period-task/SKILL.md` — read these if the extension
  touches cross-run state or period-task behavior. (Referenced here rather than
  attached to keep the launch prompt lean; read them from disk if needed.)

Constraints to name explicitly in the write-up (they are the "or not really"
half of the answer): the instantiated task path is fixed to one per template;
the run blackboard is recreated fresh each firing so cross-run state must live
in the template's own blackboard; a ticket-level `script:` runs on every step
so it only fits a one-step, ungated workflow; agent templates need a TTY /
REPL supervisor while script templates run headless.

Testing note (from `coga/contexts/coga/codebase`): recurring code has
clean-checkout-only failure modes and a packaging test that silently skips
without `hatchling`. Run `python -m pytest` and `coga validate --json` after
changes, and keep the live repo copy under `coga/` in sync with the packaged
copy under `src/coga/resources/templates/coga/` when touching shipped
contexts.

Scope boundary: this ticket is scoped to making task-specific recurring
tickets *possible and documented*. Do not build out a specific production
recurring job here — if the investigation surfaces a large, separable code
change, spin it into a follow-up ticket rather than expanding this one.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
