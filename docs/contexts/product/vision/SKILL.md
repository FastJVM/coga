---
name: product/vision
description: Coga's purpose, intended audience, kinds of work, and operating limitations; the product thesis, not a behavioral contract or measured result.
---

# Coga vision

Authority: purpose, audience, and limits. Enduring design constraints
belong to [`coga/principles`](../../coga/principles/SKILL.md); shipped behavior
belongs to the focused `coga/*` contracts; public voice belongs to
[`marketing/positioning`](../../marketing/positioning/SKILL.md). Founding history
and the original essay's arguments are in
[`docs/archive/origins.md`](../../../archive/origins.md).
[README.md](../../../../README.md) is the source of truth for concepts and
positioning; the earlier bet and work-kind mapping are in
[`docs/archive/positioning-before-readme-2026-10-13.md`](../../../archive/positioning-before-readme-2026-10-13.md).

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
(Apache-2.0) as a field report from that use.

## Intended audience

Small technical teams that already use CLI agents (Claude Code or Codex), are
comfortable with Git, the shell and markdown, and want to understand and correct
their own operating machinery. It fits when writing down how work should happen
costs less than supervising the same work indefinitely, and when the operator
can evaluate the result.

It is not for teams that want a managed service, an SLA, zero setup, a hosted
dashboard, or a delegate-and-forget substitute for an employee.

## Three kinds of work

Tasks sort by how much of the task is known before it starts:

- **Routine**: repeatable upkeep such as fixing merge conflicts or bumping
  dependencies.
- **Understood**: work you can fully specify before doing it, like a support
  request or a planned feature.
- **Unknown**: work you discover by doing. There is a known cone of what you
  have already done, and beyond it everything is blurred.

Coga is built for unknown work, learned by doing: the correction loop in
`## Purpose` exists to serve it. When a premise turns out wrong, the usual
move is to cancel the ticket and start a new one
([`coga/lifecycle`](../../coga/lifecycle/SKILL.md) owns the rule). For work
you can fully specify up front, or that has settled into a routine, tools
built for that are a better fit.

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
- **A small overlay.** Coga sits on top of what agents already provide, so it
  gets better when they do; [`marketing/strategy`](../../marketing/strategy/SKILL.md)
  says when to re-check build versus adopt.
- **Not an agent.** Coga does not generate the work or make the judgments; it is
  what the agents and the humans operate on.
