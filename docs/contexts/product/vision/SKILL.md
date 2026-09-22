---
name: product/vision
description: Coga's purpose, intended audience, product bet, and operating limitations; the product thesis, not a behavioral contract or measured result.
---

# Coga vision

Authority: purpose, audience, bet, and limits. Enduring design constraints
belong to [`coga/principles`](../../coga/principles/SKILL.md); shipped behavior
belongs to the focused `coga/*` contracts; public voice belongs to
[`marketing/positioning`](../../marketing/positioning/SKILL.md). Founding history
and the original essay's arguments are in
[`docs/archive/origins.md`](../../../archive/origins.md).

## Purpose

Coga is a way to work with AI by managing what it works from. The person and
the AI maintain the intent, instructions, relevant knowledge and working state
as files in a Git repository; Coga assembles that material into the prompt for
the next session. Work moves from an incomplete idea through clarification,
directed execution and inspection, and the correction is made to the files
that direct later work rather than to a transcript.

Coga exists so that the operator keeps understanding and owning the machine
they depend on. Every file the agent reads, the operator can read; every rule it
follows, the operator can edit. When an agent is wrong, the durable fix is a
reviewed change to a context, skill, workflow or ticket, and the next stateless
session starts from it. That short correction loop is the mechanism the rest of
the design serves: corrections are cheap enough to make routinely, so the
maintained material improves with use.

Coga began as the operating substrate of FastJVM, a two-person technical
company, and it runs the work that builds Coga. It is published as open source
(AGPL-3.0-or-later) as a field report from that use.

## Intended audience

Small technical teams that already use CLI agents (Claude Code or Codex), are
comfortable with Git, the shell and markdown, and want to understand and correct
their own operating machinery. It fits when writing down how work should happen
costs less than supervising the same work indefinitely, and when the operator
can evaluate the result.

It is not for teams that want a managed service, an SLA, zero setup, a hosted
dashboard, or a delegate-and-forget substitute for an employee.

## The bet

A two-person technical team can produce the output of a ten-person team when
agents do the mechanizable work and the humans concentrate on specification,
evaluation and correction. **This is a thesis, not a measured result.** It rests
on three conditions:

- model inference keeps getting cheaper per task;
- expertise encoded by the person who holds it compounds, because corrections
  accumulate in reusable files instead of in people's heads;
- the break-even point for automating a task has moved far enough that
  previously marginal work becomes worth automating.

Given those conditions, the limit is whether there is a substrate that captures
the leverage. The dated operating observations
([velocity evidence](../../../evidence/velocity.md)) count agent-operated
workstreams; they do not measure productivity, and the human-minutes experiment
is shelved.

Choose what to automate with three questions: is the task publicly and
extensively documented; is competent-and-generic output enough; can the result
be evaluated with the rigor you would apply to a contractor? If any answer is
no, decompose the task until each part passes, or keep doing it yourself.
Confident automation of work nobody can evaluate is the failure to avoid.

## Operating model

- **Local and attended by default.** The correction loop closes cheaply when the
  human is present while the context is fresh. Mature, stable automations may
  run with less attention, or elsewhere, only if their prompts, blackboards and
  decisions stay inspectable.
- **One ambient notification channel.** Urgent events and outcomes are posted
  where a small team already reads; see
  [`coga/notifications`](../../coga/notifications/SKILL.md).
- **Discipline substitutes for enforcement.** Update the governing file in the
  session where a mistake is seen; tune blocking per task; review maintenance
  proposals; keep contexts and skills separate and short; give every script an
  owner; ship imperfect first versions and correct them in use.

## Operating limitations

- **Scale ceiling.** One task per worker, status-as-signal coordination and Git
  as the sync layer are designed for a handful of people and break around ten.
  Past that, the internals would need replacing.
- **Discipline dependence.** Flexible plain files drift without sustained
  review. Without the practices above, Coga degrades into a task list.
- **Silent wrong answers, context drift, calibration rot, and skill/context
  conflation** are the watched failure modes; they are discipline issues, not
  automated checks.
- **Adoption cost.** Coga works best as the operating substrate, not a parallel
  one layered over established tools and tribal knowledge.
- **Linear workflows.** Dynamic or parallel orchestration belongs in an agent
  framework.
- **Self-hosted and self-supported.** There is no hosted service or support
  contract.
- **The market may absorb it.** If editors, platforms or model vendors ship
  most of this value, keep the method and retire the tool; see
  [`marketing/strategy`](../../marketing/strategy/SKILL.md).
- **Not an agent.** Coga does not generate the work or make the judgments; it is
  what the agents and the humans operate on.
