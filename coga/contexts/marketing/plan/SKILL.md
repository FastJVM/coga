---
name: marketing/plan
description: Starting point for Coga marketing work — preparation order, needed deliverables, retained essay briefs, phase gates, and execution owners. See marketing/map for sources and marketing/distribution for channels.
---

# Coga marketing plan

This is the starting point for marketing work. [marketing/map](../map/SKILL.md)
locates the documents; [marketing/positioning](../positioning/SKILL.md) owns
the pitch direction, audience and voice; [marketing/distribution](../distribution/SKILL.md)
owns channels and audience measurement. `marketing/write-post` owns the
writing and publication procedure. Product claims remain grounded in
`docs/vision.md` and the relevant Coga contracts.

## Preparation order — owner direction, 2026-09-09

1. **Extract and locate the knowledge.** The audit supplies `marketing/map`
   and `marketing/distribution`; this plan links the authored homes.
2. **List needed deliverables and proposed cuts.** The audit's current worklist
   records owners and evidence. The launch gates below remain the publication
   bar while the owner reviews the message.
3. **Make and decide, then write.** The owner clarified that the first job is
   creative and editorial: `marketing/plan/collect-public-examples-for-the-launch`
   now makes story/example options and reaches a choice with the owner.
   `marketing/plan/write-the-pitch-and-narrative` turns that decision into
   finished copy. Start from the managed-prompt direction in positioning;
   distinguish worked illustrations from claims about observed events.
4. **Review the plan, then execute cleanup.** `marketing/build-the-launch-plan`
   records the final keep/drop choices against that message. The existing
   cleanup, README, community and post tickets execute the retained work.

**Retained campaign:** three personal essays — decluttering, human
amplification, and documentation as a cache. The owner has not canceled those
tickets or approved replacement titles. Their briefs below remain working
constraints; final copy must reconcile them with the newer pitch before
publication.

**Dropped by the owner on 2026-09-09:** the paired token/time experiment and
its launch gates. Do not create `marketing/token-receipts`. The historical
protocol joins the earlier experiment and shelved proof post in
`marketing/launch-history`; it is not an attachment for live launch work.
Post 3 still needs a public example of a context being used by a later session.
Ordinary usage diagnostics and audience-response measurement remain useful.

**Excluded from launch sources:** the private-repo narrative quotations, the
superseded audit claim that no plan exists, and duplicated distribution prose.
The separate confidentiality ticket owns the private attachment's disposition.
Broader document deletion or the proposed context-root migration requires the
existing documentation ticket's review.

## The play

The launch is **not** a product announcement and **not** a public experiment.
It is a series of first-person essays on the founder's personal blog, each
carrying exactly one idea and pointing naturally at the next. The envelope for
the series is: **"this is my internal tool; I'm open-sourcing it."**

The genre is the **idea essay that names a felt pain**. The reader verifies the
thesis against their own life, so recognition and real detail matter more than
proof theater. The only publishable narrative evidence is Coga operating on
Coga: its tickets, log, diffs, and PRs are public and reproducible. That is
stronger evidence than an unverifiable quote from a private repo, but it does
not prove generality. Say once, plainly, that Coga also runs private work whose
details cannot be published; do not use those private runs as evidence.

The three angles do not replace the positioning spine. **Independence and
ownership remain the cause underneath each claim:** state leaves the founder's
head by entering a repo they own; judgment compounds because they can edit the
system directly; documentation saves reacquisition because the cached
understanding is theirs. "Amplify the human" must never stand alone as a
generic human-in-the-loop slogan. Decluttering may be post 1's felt hook, but
owned, visible state must appear in its opening argument rather than arrive as
a late defensive feature.

## Message architecture

| Post | One claim | Opponent / title brief | Must not claim | Bridge |
|---|---|---|---|---|
| 1 — declutter | Moving work and working state into a visible queue clears the founder's head without hiding the work. | Name the autonomy tradeoff or the tools that turn the human into the scheduler; keep the claim conservative. | A measured time saving, fire-and-forget autonomy, evidence from private repos, or "it works without me" as the thesis. | Once the work is out of your head, the human is not removed; their judgment becomes the scarce input. |
| 2 — amplify | One human correction can become durable guidance for every later agent session. | Name the autonomy doctrine that treats the human as residue; do not name-and-attack a vendor. | A generic "humans think" slogan, an ownership feature list, or an output/productivity multiplier. | The correction compounds only because the repo can reuse what the human taught it. |
| 3 — productivity | Documentation acts as a cache: a stateless agent can reuse grounded understanding instead of reconstructing it every run. | Name documentation-as-overhead or the belief that a larger model/context window removes grounding work. | Any measured token/time result or unsupported "faster" / "fewer tokens" claim. | Close on the practice and invite readers into the repo/community; do not tease a proof post. |

The final blog and HN titles are written in the post ticket and approved by the
owner. The HN title may differ from the blog title. Every HN candidate must
name an opponent and make a claim the body can support without numbers.

### Post 1 — it declutters your mind

The stable execution ticket is `marketing/post-async-megalaunch`; async
megalaunch is now an example inside the essay, not its thesis. Tell the story
in the present tense, never as a false genesis.

Five beats:

1. **The felt pain:** tabs, agent sessions, questions, and half-held task state
   turn the founder into the CPU and leave every open loop in their head.
2. **Make the work's inputs explicit:** show the intent, instructions,
   relevant knowledge and current state in files the founder owns. Tickets
   and blackboards hold the work; the morning queue gathers decisions that
   need judgment.
3. **Batch judgment, then leave:** answer the queue, review, brief, launch the
   sweep, close the laptop. Megalaunch illustrates the changed mental posture;
   it is not a promise of fully managed autonomy.
4. **Why that is trustworthy:** the state is readable files in the founder's
   git, blockers expose decisions instead of guessing, and every action can be
   inspected and corrected. This is where the former "you own it" idea lives.
5. **Open-source it:** link the repo and community home, own the dogfooding,
   include the one-sentence private-repo limitation, and state the real caveat:
   the first days feel like setup; the payoff arrives when the loop closes and
   then compounds.

Keep Pirsig, compile-your-company, operations-as-code, token mechanics, and
productivity results out. Real public Coga-on-Coga details replace generality.

### Post 2 — it amplifies the human

The stable execution ticket is `marketing/post-you-own-it`; it is retained but
rescoped. Ownership stays present as the enabling condition, not the post's
defensive thesis.

The post is an offensive claim about what the operator becomes able to do:

1. start with the strongest version of the objection — autonomy is supposed to
   remove the human, so a judgment loop sounds like failure;
2. show one public correction: the agent does something wrong, the
   founder edits the governing context, and a later session behaves
   differently;
3. show the amplification mechanism — one act of judgment becomes reusable
   guidance rather than a correction paid again in every session;
4. ground it in ownership: direct edits, readable state, vendor-neutral agents,
   no hidden memory; and
5. hand off to post 3: what looks like documentation is the cache that makes
   this compounding possible.

Do not lead with "keep thinking," "agents do, humans think," or a list of
local-first features. The correction and changed behavior carry the claim.

### Post 3 — productivity by mechanism

The stable execution ticket is `marketing/post-doc-as-cache`; it is retained
and sharpened, not turned into the shelved proof post.

Sessions are stateless. An undocumented repo makes each one reconstruct the
same conventions, decisions, and domain facts. Contexts buy that understanding
once and compose it into later work: **documentation becomes a cache of human
judgment.** Show the exact context and the exact question it already answered
on a later run.

Required support is the exact public context, the question it answers, and a
later session whose recorded work shows that understanding in use. A prompt
containing a context proves delivery; the later behavior supplies the reuse
example. If that second half is missing, report the gap and narrow or defer
the claim. No paired experiment, token quota, or time-to-first-edit measurement
is required. Do not claim a measured saving or general productivity effect.

## Phase 0 — make the launch real

There is **no warm-up post**. The blog's irregular history makes the current
gap normal, and the two useful checks — a subscriber baseline and a working
subscribe flow — can be completed directly.

Every gate below is cumulative. No launch date is announced and post 1 does
not publish until every blocking row is green.

| Gate | Done when | Owner |
|---|---|---|
| Product queue | Every task under `cleanup/` is done. The Python 3.11 resources fix lands before the 1.0 release. | Each cleanup-ticket assignee executes; `nicktoper` accepts/merges and owns the release decision. |
| Install path | Coga 1.0 is on PyPI and the README path passes from a clean Python 3.11 repo through a real first agent launch. Record the tested version and environment. | `nicktoper` publishes; the post-1 agent reruns and records the quickstart. |
| Landing page | `marketing/readme-top` is done and the first screen explains the approved interaction and its decluttering benefit through owned, visible state. | Ticket assignee; `nicktoper` approves. |
| Community | `marketing/discord` has created the chosen home, its repo link works, the exact URL is in the post draft, and one person can post a real question there. The live post link is rechecked on Day 0. | Ticket assignee implements; `nicktoper` chooses Discussions vs Discord. |
| Blog measurement | Before post 1, record Jetpack subscriber count, trailing-30-day views, community count, GitHub stars, and the PyPI download baseline; complete a real test of the Jetpack subscribe flow. | `nicktoper`, because the stats and subscriber account are login-gated. |
| Account decisions | Record Bookface standing and reserve a founder-present HN window. `Let047` already has sufficient age/karma; supply its joined-subreddit list, because membership and community rules are the only remaining Reddit gate. No suitable existing community means Reddit is omitted, not that the launch is blocked. | `nicktoper`. |
| Post package | Post 1 has cleared every `marketing/write-post` gate: supported beats, clarity pass, claim check, full prepared replies, owner-approved blog/HN titles, live repo/community links, and channel copy. | Post-ticket agent prepares; `nicktoper` approves and publishes. |
| Audience follow-up | Create `marketing/phase-1-retro` with the baseline, distribution context's scorecard, and dated 24-hour / 72-hour / day-14 checkpoints before post 1 ships. | `nicktoper` supplies private counters; the assigned agent collects and scores. |

Bookface is a hard pre-HN gate in `marketing/write-post`. If the owner reports
that it cannot be used, do not silently skip it: the owner must explicitly
change this plan and the skill's matching gate before any HN submission.

## Distribution

Read `marketing/distribution` for the channel matrix, Day-0 sequence,
HN/Lobsters/Reddit spacing, account evidence, titles, attribution, fixed
audience scorecard and miss branches. The blog remains canonical; the owner
publishes, takes the Bookface read before HN, and is present in the threads.

The YC channels in that context — a Launch YC post and YC's own amplification —
are product-launch shaped and therefore sit outside "the play" above rather than
replacing it. They are unscored and excluded from the phase-1 read. The owner
placed them **after phase 1, with the second run** (2026-09-09); post 1 stays a
pure essay opening. `marketing/build-the-launch-plan` tailors the exact
placement against post 2's window.

## Phase 1 — declutter launch and retro

Phase 1 starts only when all phase-0 gates are green. Ship post 1 through the
policy in `marketing/distribution`. The post agent
hands its channel timestamps and initial observations to
`marketing/phase-1-retro`; that separate ticket owns the 24-hour, 72-hour,
and day-14 checks so a writing ticket does not remain open as a hidden timer.
`nicktoper` supplies login-gated blog and community figures and makes the
phase disposition.

The fixed scorecard and miss branches live in `marketing/distribution`.
Post 2 may be drafted during observation. It does not publish until day 14,
the applicable branch work is closed, and `nicktoper` records a proceed
decision. Aim to publish within seven days of that decision.

## Phase 2 — human amplification

Ship post 2 through the same channel runbook after the phase-1 owner gate.
Its specific content gate is a public, checkable correction-loop example with
both halves: the human's edit and the changed later behavior. The prepared
replies must include the real objection that keeping a human judgment gate is
less autonomous than managed alternatives; concede the trade rather than
renaming it as autonomy.

Phase 2 is complete when its chosen channel sequence is finished and responses
and referrers are recorded. No new numeric audience threshold is invented here;
phase 1 is the pre-registered distribution test.

## Phase 3 — documentation as a cache

Post 3 waits for all of the following:

- post 2's channel sequence and response capture are complete;
- a public context and the exact question it answers are linked in the post's
  working sources;
- a later session's record supports actual reuse of that understanding; and
- the post has cleared the ordinary `marketing/write-post` and owner gates.

If evidence is missing or contradicts the proposed mechanism, narrow or
postpone the post. The owner removed the paired token/time experiment; it is
not a prerequisite. Once the content and publication gates pass, target one
to two weeks after phase 2. The series ends at post 3.

## Prepared replies

These are the standing answers, not a substitute for the full replies each
post ticket must write before shipping:

- **"Show me / where are the receipts?"** — the Coga repo is public; the
  tickets, log, diffs, and PRs behind the described day are inspectable. The
  essay claims a practice, not a measured result.
- **"It's just markdown and a CLI — I'll build it myself."** — agreement,
  never defense: simplicity is why the substrate can be owned and understood.
  The value is the compounded context and corrected discipline, not a secret
  mechanism.
- **"How many PRs / how much did it actually ship?"** — no benchmark framing.
  Point at the public repo and restate what the essay actually claims; do not
  improvise a number.
- **"You're just running it on itself."** — yes: Coga-on-Coga is the only
  public, reproducible demonstration offered here. It also runs private work,
  but unverifiable private examples are not evidence and this series does not
  claim universality.

## Claim discipline

- Descriptive claims only; **no measured productivity multiplier anywhere**.
  The one ratio Coga publishes is the two-person/output-of-ten bet in
  `docs/vision.md`, echoed in `README.md`: a thesis about what the tool is for,
  never a measured result. Keep that framing.
- Essay posts claim ideas, not results. The moment a post states a figure as a
  result, it graduates into the archived proof-post regime. Post 3's public
  source example grounds its mechanism; it does not establish a comparative
  efficiency result. `marketing/write-post` step 6 enforces this.
- Misses stay publishable. Honest caveats and limits go in the posts, not in a
  FAQ, and a failed channel threshold is recorded rather than rationalized
  away.

## Ownership

| Role | Owns |
|---|---|
| `nicktoper` | Final message and phase decisions; login-gated facts and baselines; publishing/submitting through personal accounts; the fastjvm.com announcement; founder presence in threads. |
| Post-ticket agent | Source packet, brief, stress test, outline, draft, clarity pass, claim check, full replies, title/channel options, live-link verification, public metric capture, and blackboard handoff. |
| Cleanup/readme/community ticket assignees | Their named launch precondition, with evidence of completion in that ticket. |
| Phase-1 retro agent | Public channel capture, checkpoint table, branch diagnosis, and a proposed disposition for the owner. |

External publication is an owner action. An agent prepares it and verifies the
result, but never infers permission to post from a completed draft.

## Execution tickets and disposition

- `marketing/phase-0-audit` — original checks completed; current owner review
  extracts the knowledge and hands off the worklist. Its lifecycle remains at
  the human gate until the owner advances it; do not rerun the audit.
- `marketing/plan/collect-public-examples-for-the-launch` — make story and
  example options, recommend one, and record the owner's choice. The existing
  ref is historical; this is no longer a collection brief.
- `marketing/plan/write-the-pitch-and-narrative` — use the chosen story and
  worked examples to write the reusable message and supported narrative.
- `marketing/build-the-launch-plan` — final message/sequence and keep/drop
  decision at the existing owner gate.
- Every ticket under `cleanup/` — blocking product/first-run queue.
- `marketing/readme-top` — blocking landing-page alignment.
- `marketing/discord` — blocking community-home decision and creation.
- `marketing/phase-1-retro` — create before post 1; own the dated checkpoints,
  HN second-chance branch, fixed scorecard, and owner disposition.
- `marketing/post-async-megalaunch` — **retained and rescoped** to post 1,
  mental decluttering. Async megalaunch is supporting detail; the stable slug
  is historical bookkeeping.
- `marketing/post-you-own-it` — **retained and rescoped** to post 2, human
  amplification. Ownership moves into the causal spine and post-1 trust beat;
  the stable slug is historical bookkeeping.
- `marketing/post-doc-as-cache` — **retained and sharpened** as post 3,
  documentation-as-cache mechanism, supported by a real reuse example.

None of the three post tickets is canceled. Each runs
`marketing/write-post`, which supplies the production steps and gates; this
context supplies the brief and launch state.

## What this context does NOT cover

- Channel/account facts, distribution policy and audience scoring —
  `marketing/distribution`.
- Document locations, authority and overlapping work — `marketing/map`.
- How a post is written and shipped — `marketing/write-post`, which hands its
  prose-craft pass to the imported `clarity` skill.
- Positioning, audience, voice, competitive facts, and honest product limits —
  `marketing/positioning`.
- The full strategy — `docs/market-thesis.md`; the why — `docs/vision.md`.
- The superseded experiment and proof-post machinery — archived in the
  unattached `marketing/launch-history` context, outside this composed plan.
