---
name: marketing/strategy
description: Coga's strategic market argument — where value and durability live in its category, what is and is not original, what success means, and when to re-check; reasoning, not approved copy or product behavior.
---

# Coga market strategy

Distilled from the market thesis first written 2026-05-30. This is argument,
not positioning ([README.md](../../../../README.md); claim limits in
[positioning](../positioning/SKILL.md)), not the campaign
([plan](../plan/SKILL.md)), and not product behavior. Dated competitor
facts live in the [agent memory landscape](../../../evidence/agent-memory-landscape-2026-10-13.md)
(older: [`docs/archive/market-landscape.md`](../../../archive/market-landscape.md));
re-verify any of them before a public claim.

## Thesis

In Coga's layer — a CLI that runs coding agents from Markdown files in Git, a
small overlay on what agents already provide — there is no defensible
technical moat, only taste. Taste adopted by enough people hardens into a
metaphor and a brand, and that is the only durable thing in the category (Jira
endured through the metaphor it imposed; Linear displaced it on taste with no
technical advantage). A metaphor only you use is a convention, not a moat.

Why no moat:

- Legibility and defensibility are opposites. Coga removes opacity and
  lock-in on purpose.
- The mechanism is borrowed or simple: the SKILL.md format is an open standard;
  the workflow is a linear state machine; OpenAI published a near-identical
  ticket-board skeleton (Symphony).
- Models plus open standards keep absorbing orchestration, integrations,
  memory and skills. The durable moats in the stack are the model itself and
  distribution.

## The floor: agents are capable but ungrounded

A frontier agent lacks what is not in its weights: the operator's
conventions, domain facts, recent decisions. An ungrounded capable agent acts
confidently and wrongly, so feeding it is not optional. The need is obvious
and every tool answers it; Coga's answer is one point on a known spectrum —
explicit, deterministic, author-controlled composition, scoped by process
position and maintained by a human-gated loop — against the field's opaque,
retrieval-driven, auto-captured default. That gap does not close with better
models, and the human is the only source of the missing facts.

## Where value moves — 2026-10-13 refinement

Owner argument, refined in a review session. Execution is becoming abundant,
so value per unit moves to what stays scarce around it; volume, and
thin-margin value, stay in execution and go to the vendors who sell usage.
Three things stay scarce:

- **Proprietary knowledge.** What the team decided, tried and learned is not in
  any model's weights. This is the floor above, seen from the value side.
- **Accountability.** Someone has to decide and answer for it, so high-stakes
  work keeps human gates even where an agent could do the work.
- **Differentiation.** When everyone uses the same models, an agent's default
  is the industry average. What distinguishes a system is its deviation from
  that default, which the human or a discovery step supplies and contexts
  preserve.

Capture follows location: knowledge held in a vendor's memory leaves the
leverage with the vendor; kept as owned files in the repo, it stays with the
team. This is the economic reading of explicit versus opaque composition.

Coga does not create the deviation. It solicits the model with the team's own
material and makes that solicitation durable and shared instead of a one-off
prompt; `other-agent` review also limits lock-in to one model's defaults.

Vendors sell usage, and selective injection plus human gates consume less of
it, so copying ownership and freshness runs against their incentive. Expect
convergence instead through enterprise needs (shared, versioned team
knowledge, already arriving as skills), which Coga's use of the `SKILL.md`
convention makes compatible rather than threatening. The likely trajectory is
that the ideas spread while the tool stays small, which fits success measured
as influence (`## Strategic posture`).

## Where the originality is

Not in the mechanism, and not in the workflow (the most copied primitive). The
most distinctive primitive pair is statelessness plus the blackboard: the
prompt is a function of the files now, so an edit between runs takes full,
inspectable effect. Also under-stated: step boundaries as deliberate context
resets, and status-as-signal instead of a lock. The residue is the direction —
owned, legible, vendor-neutral, human-gated correction — chosen while the field
moves toward absorption. Competitors can build any piece; model vendors are
poorly placed to center "depend on vendors less". Original in stance, freely
copyable for the same reason. See the dated
[landscape](../../../evidence/agent-memory-landscape-2026-10-13.md) before
saying "first" or "only": neither is supported.

## Strategic posture

Current campaign choices are in [plan](../plan/SKILL.md) and message in
[positioning](../positioning/SKILL.md).

Success is measured as influence or a committed small user base, not commercial
dominance; the traits that make Coga defenseless commercially are neutral for
that metric. Two gates: make the idea sayable without the reading list, and
prove the felt loop in real use.

## Re-check triggers

- **Build-vs-adopt:** when an incumbent does most of what Coga does for us,
  migrate the method and retire the tool.
- **A neutral, opinionated builder** running the Linear play for agent
  operations narrows the window for a branded category (position B in the
  [archived posture](../../../archive/positioning-before-readme-2026-10-13.md)).
- **Model vendors climbing into the substrate** (skills, managed agents).
- **Landscape facts:** re-verify competitor claims before reuse.
