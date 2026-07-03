---
name: autonomy/triage
description: Three-question test for deciding how much of a task AI may own and which autonomy tier applies.
---

# Autonomy triage

Use this context to decide how much of a task AI may own. It encodes the Test
stage from "Audit, Test, Automate: how we decide what AI can own"
(https://deviantabstraction.com/2026/06/02/audit-test-automate-how-we-decide-what-ai-can-own/).
Audit is the periodic human inventory practice; Automate is the chosen tier
workflow doing the work. This context is only the per-task test.

## The 3-question test

A task may be delegated to AI only if it passes all three questions:

1. **Publicly documented?** The task is public or conventional enough that the
   agent likely knows the domain. Private, idiosyncratic, or tacit work leans
   human.
2. **Conventional result acceptable?** Average or conventional quality is good
   enough. Work that needs above-average, differentiating taste or judgment fails
   this question.
3. **Verifiable, or bounded failure?** The output can be directly verified, or
   the worst plausible failure is bounded and reversible enough to tolerate.

Never spend more time reviewing the AI's work than a human would have spent doing it.

## Four tiers

- **fully-automated** — all three questions pass and the failure radius is low.
  The task can run unattended.
- **assist-only** — Q2 fails: the task is feasible, but conventional output is
  not good enough. The AI assists; a human owns the result.
- **human-verify** — the work is verifiable or bounded, but the failure radius is
  medium or high. The agent may prepare the task end to end, but a human reviews
  before the irreversible step.
- **human-only** — Q1 fails outright, or the task is structurally unverifiable
  with high failure radius. The human performs it; the agent only supports
  read-only.

Each tier is realized by the `assignee:` choices in its matching `autonomy/`
workflow.

## What this context does NOT cover

- Browser-specific automation routing. `browser/build-automation` has its own narrower failure-radius triage.
- Workflow wiring or timing. This context defines the rubric; workflow selection decides when to apply it.
- The Audit stage. Periodic human inventory is outside this context.
