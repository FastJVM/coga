---
slug: marketing/build-the-launch-plan
title: Build the launch plan
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

Build the launch plan. `marketing/phase-0-audit` did the two jobs it was for —
identify the points to fix, and gather the information a plan needs — and both
are done. What does not exist yet is the plan itself: what ships, in what
order, through which channels, gated on what. The owner named the message
architecture on 2026-09-03 as three angles: **it declutters your mind**, then
**it amplifies the human**, then **productivity**. Turn that plus the audit's
findings into an operational launch plan.

## Context

**The distinction this ticket rests on.** The three angles are the *message*
— what we say and in what order. The launch plan is the *operation* — what
ships when, where, and on what preconditions. The existing
`coga/contexts/marketing/plan` context holds a lot of settled thinking about
the message and almost nothing about the operation, which is the gap.

### Input 1 — the three angles (owner, 2026-09-03)

In this order, each recruiting for the next:

1. **It declutters your mind.**
2. **It amplifies the human.**
3. **Productivity.**

The owner gave the skeleton, not the flesh. The plan decides how these map to
posts: one post per angle or otherwise, what each claims, and what each must
not claim.

Three things the mapping has to resolve, found while comparing the angles
against the current series:

- **Angle 1 sharpens the plan against its own rule.** The plan says the
  converting genre is "the idea essay that names a felt pain". Today's post 1
  promises a capability, "it works without me". Decluttering promises a felt
  state. The second is the genre the plan already committed to.
- **Angle 2 is not today's post 2.** Amplification is an offensive claim about
  what the human becomes capable of; today's post 2, "you own it", is a
  defensive claim about why the tool is safe to adopt. Ownership is the answer
  to the question angle 1 provokes — why would I trust my days to this — so it
  needs a home rather than quietly disappearing: folded into angle 1, kept as
  its own post, or demoted into the prepared replies.
- **Angle 3 collides with the claim discipline.** "Productivity" is exactly
  the claim the plan forbids stating as a result; the moment a post states a
  figure as a result it graduates into the shelved proof-post regime. Angle 3
  has to argue *mechanism* (why the loop is faster), not *outcome* (how much
  faster it made me). The doc-as-cache argument is already the mechanism form
  of that claim.

### Input 2 — what the audit gathered

All of it is on `marketing/phase-0-audit`'s blackboard. The parts a launch
plan needs:

- **Channels, with real standing.** HN `top256`: karma 213, three front-page
  hits at 87/47/32 points on plain essay titles, both Show HN attempts
  flopped, one resubmission four days later took. Lobsters `ntoper`: 15-month
  account, karma 55, one prior self-authored submission of a
  `deviantabstraction.com` essay at 26 points / 19 comments, so the domain is
  already seen and the new-account restrictions do not apply; tags are
  `vibecoding` + `practices`, never `ai`. Reddit `Let047`: 7,781 karma, 2,609
  contributions, 6 years, 56 followers — not a cold account, but the joined
  subreddits are still unknown and decide whether Reddit is in the set.
  Bookface: owner-only, still unreported.
- **The blog can do newsletter day one.** WordPress.com with a Jetpack
  subscribe block already wired and Jetpack Stats for referrers. Last post
  2026-06-02, three months quiet, zero Coga mentions. Attribution is
  referrer-level only, which the owner accepted; the baseline subscriber count
  and monthly views must be recorded *before* post 1 or every delta is
  unmeasurable.
- **fastjvm.com** gets a launch announcement but is not a phase-1 channel and
  carries no short-term weight (owner, 2026-09-03).
- **Preconditions are ticketed.** Nine drafts under `coga/tasks/cleanup/`,
  including the 1.0 release and the Python 3.11 fix that gates it. There is no
  working first run from PyPI until that release lands, so no post can ship
  before it.
- **Community home does not exist yet** — Discussions disabled, no Discord,
  no repo homepage URL. `marketing/discord` decides; the post needs a
  "where to go" link before it ships.
- **Prepared replies do not exist** outside four bullets in the plan context.
  The plan requires them written before post 1.
- **Evidence is constrained to Coga on Coga.** Every non-Coga narrative
  candidate was ruled confidential. The audit recorded a reframe worth
  weighing: a private-repo quote is unverifiable, while `FastJVM/coga` is
  public and reproducible by anyone who clones it. The cost is the "does it
  work on anything but itself" objection, best handled by one honest sentence
  rather than silence.

### What the plan must actually specify

The operation, not the message. At minimum: the ordered sequence of what
ships; which channel each post goes to and in what order within a launch day;
the preconditions each ship gate waits on; who owns each step; the phase-1
thresholds and what a miss triggers; and where the token receipts for the
productivity angle get collected during earlier phases.

### What is settled and not reopened

- **Fork A** — an internal tool, open-sourced, told as a personal story.
- **Claim discipline** — descriptive claims only, no measured productivity
  multiplier, misses stay publishable.
- **Personal essays on the founder's blog**, first person, present tense, real
  concrete detail, one idea per post.
- **Distribution tactics** — titles are the experience never the thesis, never
  solicit upvotes, the HN second-chance branch, founder present in the thread.
- `marketing/positioning` and `docs/market-thesis.md` stay authoritative; if
  this plan drifts from them, they win.

### Out of scope

- Writing any post. This produces the plan; the post tickets write the posts.
- The `cleanup/` preconditions, which have their own tickets.
- Re-opening fork A, the claim discipline, or the blog-essay format.

### Where the output lands

`coga/contexts/marketing/plan/SKILL.md`, updating the phases, the post
definitions, and the execution-ticket list, and leaving the settled sections
intact. Say explicitly what becomes of `marketing/post-async-megalaunch`,
`marketing/post-you-own-it`, and `marketing/post-doc-as-cache` — retitled,
rescoped, or canceled.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
