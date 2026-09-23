---
name: marketing/strategy
description: Coga's strategic market argument — where value and durability live in its category, what is and is not original, what success means, and when to re-check; reasoning, not approved copy or product behavior.
---

# Coga market strategy

Distilled from the market thesis first written 2026-05-30. This is argument,
not approved public voice ([positioning](../positioning/SKILL.md)), not the
campaign ([plan](../plan/SKILL.md)), and not product behavior. Dated competitor
facts live in [`docs/archive/market-landscape.md`](../../../archive/market-landscape.md);
re-verify any of them before a public claim.

## Thesis

In Coga's layer — agent orchestration, knowledge management, ticketing — there
is no defensible technical moat, only taste. Taste adopted by enough people
hardens into a metaphor and a brand, and that is the only durable thing in the
category (Jira endured through the metaphor it imposed; Linear displaced it on
taste with no technical advantage). A metaphor only you use is a convention,
not a moat.

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

## What kind of thing Coga is

Coga is better read as a discipline than a technology: operations-as-code,
treating knowledge, process and the work itself as versioned, legible,
agent-executable files. Earlier "X-as-code" disciplines waited for an executor
for their domain; operations waited for an executor that tolerates natural
language. The executor is domain-agnostic, so one substrate spans deterministic
steps (a ticket's `ticket.py`), judgment steps (an agent) and irreversible ones
(script plus human gate). Coga orchestrates existing systems; it does not
replace them. Its contrarian sub-bet is that the discipline needs a thin
runtime — validation, supervised launches, vendor-neutral agents, recurring
work, an audit log — without hiding state.

## The imposed metaphor: compile your company

Coga's taste is impositional where Linear's is subtractive. It asks the
operator to decompose work to evaluable units, externalize tacit knowledge,
classify facts versus procedures, separate durable truth from working state,
and correct the rule rather than the instance. The rigor is paid into the
substrate once and inherited by later light tasks, and agents do much of the
drafting. The cost is a standing demand for judgment, which narrows the
audience to people who enjoy rigor. The lesson from Linear is to subtract
friction from being rigorous, not to remove the rigor.

For an agent-mediated tool without its own UI, felt taste lives in the
correction loop snapping shut and in reliably steered agent behavior.

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
[claim check](../../../archive/market-landscape.md) before saying "first" or
"only": neither is supported.

## Strategic posture

Two positions were analyzed: A, internal open-source infrastructure published as
a field report; B, a branded category earned through adoption (the Linear
playbook with a small-tribe ceiling). A was the default with B left optional;
openness makes Coga a complement an incumbent can use as well as copy. The
earlier pinned fork is reference, not a live decision: current campaign choices
are in [plan](../plan/SKILL.md) and message in [positioning](../positioning/SKILL.md).

Success is measured as influence or a committed small user base, not commercial
dominance; the traits that make Coga defenseless commercially are neutral for
that metric. Two gates: make the idea sayable without the reading list, and
prove the felt loop in real use.

## Re-check triggers

- **Build-vs-adopt:** when an incumbent does most of what Coga does for us,
  migrate the method and retire the tool.
- **A neutral, opinionated builder** running the Linear play for agent
  operations narrows the window for position B.
- **Model vendors climbing into the substrate** (skills, managed agents).
- **Landscape facts:** re-verify competitor claims before reuse.
