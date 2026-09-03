---
slug: marketing/rebuild-the-launch-plan-around-the-three-angles
title: Rebuild the launch plan around the three angles
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-coga
    skills: []
    assignee: agent
secrets: null
step: 1 (agent-produces)
---

## Description

Rebuild the Coga launch messaging plan around the three angles the owner
named on 2026-09-03: **it declutters your mind**, then **it amplifies the
human**, then **productivity**. The current plan in
`coga/contexts/marketing/plan` is organized around a different progression and
one of its preconditions has failed, so the series needs re-deciding before
any post is written. Output: a revised plan the owner signs off, landed in the
`marketing/plan` context.

## Context

**Why now.** `marketing/phase-0-audit` checked the current plan's phase-0
preconditions against reality and found one false: the plan builds post 1 on
real quotable examples from non-Coga repos, and the owner ruled every
candidate confidential. The owner's conclusion (2026-09-03): "the plan doesn't
work; the only thing we can use is coga building coga as evidence, and we
don't have a real plan yet." The audit ticket's `## Plan premise failure`
section carries the detail. This ticket is the re-decision.

**The three angles, as given.** In this order, each recruiting for the next:

1. **It declutters your mind.**
2. **It amplifies the human.**
3. **Productivity.**

The owner supplied the skeleton, not the flesh. Step 1's job is to turn it
into a plan: one post per angle or otherwise, what each post claims, what it
must not claim, what order they ship in, and what the existing post tickets
become.

### What the current plan has, and how it maps

The existing series is a **topic ladder** — practice, then trust, then
mechanism:

| Current post | Ticket | Its angle |
|---|---|---|
| 1. "async megalaunch" | `marketing/post-async-megalaunch` | The day shape. "You launch the wave and you leave", plus the double requirement: leave *and* still see. |
| 2. "you own it" | `marketing/post-you-own-it` | Ownership, control, simplicity. In your repo, not their cloud. Answers "why would I trust my days to this?" |
| 3. "documentation as cache" | `marketing/post-doc-as-cache` | Stateless sessions re-buy understanding; contexts are that understanding bought once. Benefits from receipts. |

The three angles are a **promise ladder** instead — relief, then leverage,
then output. The mapping is not one-to-one, and the gaps are where the work
is:

- **Angle 1 against post 1.** Close, but the promise changes. Post 1 currently
  promises a capability, "it works without me". Decluttering promises a felt
  state, "your head is no longer the place the work lives". The plan's own
  genre rule says the converting form is "the idea essay that names a felt
  pain", so angle 1 sharpens the plan against its own standard. Post 1's
  existing beat 1 already names the pain exactly — chained state, terminal
  tabs, context-switching, *you are the CPU*.
- **Angle 2 is not post 2.** Amplification is an offensive claim about what
  the human becomes capable of; ownership is a defensive claim about why the
  tool is safe to adopt. Angle 2 is closer to `coga/principles` #2, "agents
  do, humans think", and to the vision's two-person/ten-person bet.
- **"You own it" has no slot in the three angles, and dropping it would be a
  mistake.** It is the answer to the question angle 1 provokes: why would I
  trust my days to this? It has to go somewhere — folded into angle 1 as the
  reason the relief is trustworthy, kept as its own post between angles, or
  demoted into the prepared replies. That is a real decision, not a detail.
- **Angle 3 has a landmine.** "Productivity" is precisely the claim the
  plan's own claim discipline forbids stating as a result: no measured
  multiplier, ever, and the moment a post states a figure as a result it
  graduates into the shelved proof-post regime. Angle 3 must therefore argue
  productivity as a **mechanism** (why the loop is faster) rather than as an
  **outcome** (how much faster it made me). Post 3's doc-as-cache argument is
  already the mechanism form of exactly this claim, so it is the natural
  vehicle, but the framing has to be explicit or the post will drift.

### What must survive the rebuild

These are settled and are not reopened here:

- **Fork A** — an internal tool, open-sourced, told as a personal story.
  The envelope "this is my internal tool, I'm open-sourcing it" is
  structurally unattackable and stays.
- **Claim discipline** — descriptive claims only, no measured productivity
  multiplier anywhere, misses stay publishable. The one published ratio is
  the two-person/ten-person *bet* in `docs/vision.md`, framed as a bet.
- **Personal essays on the founder's blog**, first person, present tense,
  real concrete detail, one idea per post.
- **Distribution tactics** — titles are the experience never the thesis,
  never solicit upvotes, the HN second-chance branch, founder present in the
  thread.

### The evidence question this plan must answer

The audit's finding stands: non-Coga evidence is unavailable, so Coga running
on Coga is the only usable source. The audit recorded a reframe worth weighing
rather than assuming the worst: a quote from a private repo is unverifiable,
while `FastJVM/coga` is public and every claim from its log is reproducible by
anyone who clones it. What that costs is the answer to "does this work on
anything but itself", and the honest handling is to say the other repos exist
and are private rather than leave the question hanging. The rebuilt plan has
to state its evidence posture explicitly instead of inheriting one.

### Out of scope

- Re-opening fork A, the claim discipline, or the blog-essay format.
- Writing any of the posts. This ticket produces the plan; the post tickets
  write the posts.
- The phase-0 worklist items already ticketed under `cleanup/`.
- `marketing/positioning`, which stays authoritative. If this plan drifts from
  positioning or `docs/market-thesis.md`, they win.

### Where the output lands

`coga/contexts/marketing/plan/SKILL.md`, replacing the sections the rebuild
changes and leaving the settled ones intact. Update the phase list and the
execution-ticket list in the same change, and say what happens to
`marketing/post-async-megalaunch`, `marketing/post-you-own-it`, and
`marketing/post-doc-as-cache` — retitled, rescoped, or canceled.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
