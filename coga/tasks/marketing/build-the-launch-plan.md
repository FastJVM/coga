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

**Scope: this ticket owns both the message and the operation.** It was first
written around a split — the three angles are the message, the plan is the
operation — and that split did not survive the 2026-09-03 evidence review.
Once post 1's spine is in question (a practice story versus a contrarian
claim naming an opponent), the message decision *drives* the sequencing rather
than sitting beside it. So both are in scope here. The existing
`coga/contexts/marketing/plan` context holds a lot of settled thinking about
the message and almost nothing about the operation, and one of its message
rules has already been corrected against evidence.

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

### Evidence: what actually works on this HN account

Verified 2026-09-03 against the public HN search API, not inherited from the
audit. The audit's figures were close but two were wrong: it reported 101
submissions, which counted comments — there are **26 stories** — and it missed
a fourth high scorer, "VC and the marginal-dollar problem" (52 points, 2017).
The API records points, not placement, so "front page" is an inference
everywhere it appears, near-certain at 87 points and merely likely at 32.

**The natural experiment.** One URL was submitted twice, four days apart, and
the only variable that changed was the title:

| Date | Title | Result |
|---|---|---|
| 2024-11-21 | "Making All Software Faster: Experiments with Bytecode on Real-World Apps" | 1 point |
| 2024-11-25 | "Computing Industry Doesn't Care about Performance: how I made things faster" | 32 points |

Both point at `deviantabstraction.com/2024/10/24/faster-computer/`. Same
article, same account, same week. A descriptive title scored 1; an adversarial
one scored 32. The audit read this resubmission as evidence for the
second-chance branch and missed that the title had been rewritten, which is
what actually moved it.

**The pattern that separates hits from misses.** Every story this account has
scored well with names an opponent: tech inevitability, the computing
industry, Copilot, VC. Every miss is descriptive, definitional, or a Show HN.
Six Show HN attempts, zero hits, best result 6 points.

| Shape | Result |
|---|---|
| Contrarian thesis naming an opponent | 87, 52, 32 points |
| Benchmark against a famous product | 47 points |
| Show HN (six attempts) | 1 to 6 points |
| Tutorial or explainer | 1 to 3 points |
| Descriptive or definitional title | 1 to 3 points |

**Consequence: the plan's title rule is wrong for this account.** The plan says
"titles are the experience, never the thesis — a thesis title gets argued
before it gets read." Every hit here is a thesis title, and the best result
ever ("Why Tech Inevitability is Self-Defeating") is pure thesis. The rule has
to be rewritten to match the evidence: name an opponent, and make the claim
conservative rather than grand. The blog-to-HN retitles show the same hand —
"Against Tech Inevitability" became "Why Tech Inevitability is Self-Defeating",
and "Beats gpt5 by 4X" became "beats Copilot by 2x", a smaller number against
a more recognizable target.

**What the one AI-workflow data point does and does not show.** "AI Delegation
Starts with Inspectable Work" (2026-06-03) scored 1 point, and it is the
closest thing in this history to post 1 as currently planned. It is *not*
evidence that the category fails: the owner confirms it was written for
himself and his team and was never a launch attempt. Timing does not explain
it either — it went out Wednesday 12:18 ET, essentially the same slot as the
87-point best (Wednesday 13:09 ET); across all 26 stories the submission
window is a near-constant around midday ET and has no explanatory power. What
it does show is the title pattern again: "AI Delegation Starts with
Inspectable Work" is a definition with no opponent in it.

**The owner's own read, and why it points the same way** (2026-09-03): the AI
category felt "too noisy to really stick out." That instinct and the natural
experiment agree. In a saturated category a descriptive title is invisible and
an adversarial thesis is not. The plan already owns a usable opponent —
autonomy tools liberate by blinding you, supervision keeps you seeing by
keeping you chained — but it is buried as beat 3 of post 1. It probably wants
to be the spine.

**Sequencing precedent.** The 32-point story was published on the blog
2024-10-24 and not submitted to HN until 2024-11-25, a month later. Publish
first, submit later is this account's own precedent, not a novel proposal.

### Blog rhythm: no warm-up post needed

Checked 2026-09-03 against the WordPress API. 39 posts since 2023, and the
cadence is extremely uneven by nature: bursts of near-daily posting in May
2024 alongside gaps of 117 days, 149 days, and 233 days immediately before the
most recent post. A three-month silence is **shorter** than this blog's normal
gap, so the "looks abandoned" concern that motivated a warm-up post is
unfounded. The two reasons that did survive — needing a subscriber baseline
and needing to know the subscribe flow works — are both satisfiable without
publishing: read the existing stats for the 2026-06-02 post, and test the
Jetpack form directly. **Do not schedule a warm-up post.**

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

### Also in scope: shelve the old apparatus, and sequence against the comms ticket

Two housekeeping jobs on the same context file, folded in here rather than
given a third ticket, because a third writer on
`coga/contexts/marketing/plan/SKILL.md` would mostly generate conflicts.

**Shelve what is no longer live.** The context still carries two blocks that
no post 1-3 may spend, and every ticket attaching `marketing/plan` pays for
them in its composed prompt:

- The **"Later, gated — the proof post"** block, 1,203 bytes: the 2-week
  pre-registered experiment, the metrics script, the token ledger, the
  intention-to-treat rule. It survives as an option, not a plan, and the
  context already tells readers not to spend any of it on posts 1-3.
- The **superseded-program status preamble**, 884 bytes, explaining that this
  plan replaced the "20 minutes a day" experiment program in August 2026.
  Real history, but history.

Together about 2.1 KiB of a 16.5 KiB context, so roughly 13 percent. Move
them somewhere durable rather than deleting them — `docs/` or a separate
context — and leave a one-line pointer, the same treatment the phase-0 audit's
evidence just got. Deciding whether the proof post is still a live option is
itself a plan decision, which is why it belongs to this ticket.

**Sequence behind `no-comms-writing-skill-the-process-is-smeared-thro.`**
That ticket is already `in_progress` at step 1 and will thin *procedure* out
of both marketing contexts into a new `coga/skills/marketing/write-post`
skill, importing `addyosmani/clarity` for the prose-craft layer. It
deliberately leaves plan status, phasing and scheduling in `marketing/plan` —
which is exactly what this ticket rewrites. The two do not overlap in content
but they do overlap in file, so **let the comms ticket land first** and
rewrite what remains. Its change is also the larger size win: procedure moved
into a skill composes only when a workflow step calls for it, whereas the
context composes for all eight tickets that attach it.

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
