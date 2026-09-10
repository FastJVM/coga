# Previous campaign ticket briefs — archived 2026-09-10

These are the task bodies before the owner requested a fresh start. They
preserve ideas and dated research for reference; they are not current briefs
or publication instructions. Some text already contradicted later decisions:
in particular the post-2 token-receipt sentence was stale when archived, and
HN points never established observed front-page placement. Use the current
[plan](../plan/SKILL.md), [source limits](../positioning/SKILL.md) and
[dated distribution evidence](../distribution/SKILL.md) when reusing material.
Existing task metadata and unrelated blackboard history remain in their tasks.

## build-the-launch-plan

Source: [coga/tasks/marketing/build-the-launch-plan.md](../../../tasks/marketing/build-the-launch-plan.md).

### Description

Review and finalize the launch plan against the selected story/examples and the
owner's newer pitch direction. `marketing/plan` already holds the retained
three-post campaign and its gates; the remaining work is the owner's message,
sequence and keep/drop decision, followed by a current handoff to execution.

`marketing/plan/collect-public-examples-for-the-launch` makes story/example
options and records the owner's choice;
`marketing/plan/write-the-pitch-and-narrative` supplies the reusable message.
Use those outputs here instead of independently commissioning the same work.
The owner dropped the marketing token experiment on 2026-09-09.

### Context

**Current handoff, 2026-09-09.** The audit's reusable material has moved to
`marketing/map` and `marketing/distribution`. The newer managed-prompt
direction is recorded in `marketing/positioning`; the writing tickets above
own the story/example decision and final pitch prose. This ticket retains the final
campaign decision at its existing human gate. The three essay tickets remain
retained until that decision changes them. Audience scoring stays in scope;
token/time measurement and receipt quotas are removed.

The older research and angle discussion below are background. Account evidence
and channel rules now have their authored home in `marketing/distribution`;
do not use their September 3 status statements as current certification.

**Scope: this ticket owns both the message and the operation.** It was first
written around a split — the three angles are the message, the plan is the
operation — and that split did not survive the 2026-09-03 evidence review.
Once post 1's spine is in question (a practice story versus a contrarian
claim naming an opponent), the message decision *drives* the sequencing rather
than sitting beside it. So both are in scope here. The existing
`coga/contexts/marketing/plan` context holds a lot of settled thinking about
the message and almost nothing about the operation, and one of its message
rules has already been corrected against evidence.

#### Input 1 — the three angles (owner, 2026-09-03)

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

#### Input 2 — what the audit gathered

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

#### What the plan must actually specify

The operation, not the message. At minimum: the ordered sequence of what
ships; which channel each post goes to and in what order within a launch day;
the preconditions each ship gate waits on; who owns each step; the phase-1
thresholds and what a miss triggers; and which public examples support the
message. The token-measurement requirement was removed on 2026-09-09.

#### Evidence: what actually works on this HN account

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

#### Blog rhythm: no warm-up post needed

Checked 2026-09-03 against the WordPress API. 39 posts since 2023, and the
cadence is extremely uneven by nature: bursts of near-daily posting in May
2024 alongside gaps of 117 days, 149 days, and 233 days immediately before the
most recent post. A three-month silence is **shorter** than this blog's normal
gap, so the "looks abandoned" concern that motivated a warm-up post is
unfounded. The two reasons that did survive — needing a subscriber baseline
and needing to know the subscribe flow works — are both satisfiable without
publishing: read the existing stats for the 2026-06-02 post, and test the
Jetpack form directly. **Do not schedule a warm-up post.**

#### What is settled and not reopened

- **Fork A** — an internal tool, open-sourced, told as a personal story.
- **Claim discipline** — descriptive claims only, no measured productivity
  multiplier, misses stay publishable.
- **Personal essays on the founder's blog**, first person, present tense, real
  concrete detail, one idea per post.
- **Distribution tactics** — titles are the experience never the thesis, never
  solicit upvotes, the HN second-chance branch, founder present in the thread.
- `marketing/positioning` and `docs/market-thesis.md` stay authoritative; if
  this plan drifts from them, they win.

#### Also in scope: shelve the old apparatus, and sequence against the comms ticket

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

#### Out of scope

- Writing any post. This produces the plan; the post tickets write the posts.
- The `cleanup/` preconditions, which have their own tickets.
- Re-opening fork A, the claim discipline, or the blog-essay format.

#### Where the output lands

`coga/contexts/marketing/plan/SKILL.md`, updating the phases, the post
definitions, and the execution-ticket list, and leaving the settled sections
intact. Say explicitly what becomes of `marketing/post-async-megalaunch`,
`marketing/post-you-own-it`, and `marketing/post-doc-as-cache` — retitled,
rescoped, or canceled.

## post-async-megalaunch

Source: [coga/tasks/marketing/post-async-megalaunch.md](../../../tasks/marketing/post-async-megalaunch.md).

### Description

Write and ship launch post 1 — **it declutters your mind** — following the
five beats and phase-1 runbook in `marketing/plan`. The stable task slug is
historical: async megalaunch is one concrete example of batching judgment and
leaving, not the post's thesis.

Use only public, reproducible Coga-on-Coga details as evidence. Own the
dogfooding and the limit: Coga also runs private work, but private examples are
not evidence this essay can offer. Fold ownership into the trust beat rather
than spinning it into a second idea. Do not claim a measured time saving or
fully managed autonomy.

Write the complete comment-section replies before shipping. Execute the
channel order in the plan, including the one-time fastjvm.com announcement,
then hand channel timestamps and initial observations to
`marketing/phase-1-retro`, which owns the day-14 scorecard and owner
disposition.

### Context

`marketing/write-post` is the order of work and the gates for this post; it is
attached under `skills:`. It reads the two marketing contexts for what to say
and hands the prose-craft pass to the imported `clarity` skill at
`coga/skills/clarity/SKILL.md`. Follow its steps rather than re-deriving a
process from the contexts. The display title is decided during that process;
the ticket's older bookkeeping name does not constrain it.

## post-you-own-it

Source: [coga/tasks/marketing/post-you-own-it.md](../../../tasks/marketing/post-you-own-it.md).

### Description

Write and ship launch post 2 — **it amplifies the human** — after the phase-1
owner gate in `marketing/plan`. The stable task slug is historical: ownership
is the enabling condition for amplification, not this post's defensive thesis.

Build the essay around one public, checkable correction loop: the agent's
mistake, the human's edit to the governing context, and changed behavior in a
later session. Make the offensive claim that one act of judgment becomes
durable guidance. Do not lead with a generic human-in-the-loop slogan, a list
of local-first features, or a productivity result. Complete the plan's channel
sequence and capture its responses/referrers while token-receipt collection
continues.

### Context

`marketing/write-post` is the order of work and the gates for this post; it is
attached under `skills:`. It reads the two marketing contexts for what to say
and hands the prose-craft pass to the imported `clarity` skill at
`coga/skills/clarity/SKILL.md`. Follow its steps rather than re-deriving a
process from the contexts. The display title is decided during that process;
the ticket's older bookkeeping name does not constrain it.

## post-doc-as-cache

Source: [coga/tasks/marketing/post-doc-as-cache.md](../../../tasks/marketing/post-doc-as-cache.md).

### Description

Write and ship launch post 3 — **productivity, by mechanism** — per phase 3 of
`marketing/plan`. Sessions are stateless, so an undocumented repo makes an
agent reconstruct the same understanding every run; contexts turn
documentation into a cache of human judgment.

Before drafting, link the exact public context, the question it answers, and
a later session's record showing that understanding in use. Begin with the
selected examples from `marketing/plan/collect-public-examples-for-the-launch`;
report a missing second half instead of inventing reuse. The ordinary phase
and owner gates in `marketing/plan` still apply.

The owner dropped the paired token/time experiment on 2026-09-09. No paired
runs, receipt quota, or token-measurement ticket is required. This remains an
idea essay: do not claim a measured saving, a productivity multiplier, or
generality from a single example. If the source contradicts the mechanism,
narrow or replace the claim.

### Context

`marketing/write-post` is the order of work and the gates for this post; it is
attached under `skills:`. It reads the two marketing contexts for what to say
and hands the prose-craft pass to the imported `clarity` skill at
`coga/skills/clarity/SKILL.md`. Follow its steps rather than re-deriving a
process from the contexts.

## readme-top

Source: [coga/tasks/marketing/readme-top.md](../../../tasks/marketing/readme-top.md).

### Description

Align the top of the README with the revised post-1 story (see
`marketing/plan`): Coga gets agent work and working state out of your head
without hiding either from you. The day shape — batch judgment, launch the
sweep, leave — is supporting evidence; owned, visible repo state is why the
promise is trustworthy. Say what Coga is and who it is for in the first
screen. Every convinced reader clicks the repo link; the README is the landing
page. Top only — not a full rewrite.

### Context

## discord

Source: [coga/tasks/marketing/discord.md](../../../tasks/marketing/discord.md).

### Description

Right-size and create the Coga community home, wired as the "where to go"
link for the launch posts. Decide in this ticket: GitHub Discussions first
(honest size for a fresh OSS repo, upgrade later) vs Discord now — an empty
Discord visible to arrivals is negative signal. Either must exist before
`marketing/post-async-megalaunch` ships — spike readers are not recoverable
after the fact. Replaces the canceled `marketing/relay-discord` (deleted).

### Context
