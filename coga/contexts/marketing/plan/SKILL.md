---
name: marketing/plan
description: The operational Coga launch plan — three gated personal essays moving from mental decluttering, to human amplification, to productivity by mechanism. Attach alongside marketing/positioning to marketing/comms tickets.
---

# Coga marketing plan

The operational plan for Coga's launch. When this drifts from
`marketing/positioning` or `docs/market-thesis.md`, they win — update this
file in the same change. The procedure for producing and shipping one post is
`marketing/write-post`; this context owns what ships, in what order, through
which channels, and behind which gates.

**Live plan (2026-09-04).** Fork A remains pinned: an internal tool,
open-sourced, told as a personal story. The series moves through three angles,
in this order, each recruiting for the next:

1. it declutters your mind;
2. it amplifies the human;
3. productivity, argued by mechanism rather than claimed as a result.

The superseded "20 minutes a day" experiment and the later proof-post
apparatus are archived in `marketing/launch-history`, an unattached context
that does not compose into launch work. The proof post is a shelved option, not
phase 4 of this launch and not a current execution ticket. Reopening it
requires a fresh owner decision after the essay series lands and megalaunch
has held up under sustained daily use.

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
| 3 — productivity | Documentation acts as a cache: a stateless agent can reuse grounded understanding instead of reconstructing it every run. | Name documentation-as-overhead or the belief that a larger model/context window removes grounding work. | Any measured token/time result, even an unquantified "faster" or "fewer tokens" conclusion from the receipts. | Close on the practice and invite readers into the repo/community; do not tease a proof post. |

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
2. **Put the state somewhere:** tickets and blackboards hold the work; the
   morning queue gathers the decisions that actually need judgment.
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
2. show one public two-minute correction: the agent does something wrong, the
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

The receipt set collected during phases 1–2 is required working source
support. It tests whether the premise survives and helps select the concrete
example; its values are not copy. The Coga repo is public, so a ticket
blackboard is visible even though the essay does not publish the result. If the
receipts contradict the premise, cut or narrow the claim. Publishing a token
delta, time delta, multiplier, or even a measured "it was faster" moves the
post into the proof-post regime and is forbidden in this series.

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
| Landing page | `marketing/readme-top` is done and the README first screen echoes decluttering through owned, visible state rather than the old capability-first story. | Ticket assignee; `nicktoper` approves. |
| Community | `marketing/discord` has created the chosen home, its repo link works, the exact URL is in the post draft, and one person can post a real question there. The live post link is rechecked on Day 0. | Ticket assignee implements; `nicktoper` chooses Discussions vs Discord. |
| Blog measurement | Before post 1, record Jetpack subscriber count, trailing-30-day views, community count, GitHub stars, and the PyPI download baseline; complete a real test of the Jetpack subscribe flow. | `nicktoper`, because the stats and subscriber account are login-gated. |
| Account decisions | Record Bookface standing and reserve a founder-present HN window. `Let047` already has sufficient age/karma; supply its joined-subreddit list, because membership and community rules are the only remaining Reddit gate. No suitable existing community means Reddit is omitted, not that the launch is blocked. | `nicktoper`. |
| Post package | Post 1 has cleared every `marketing/write-post` gate: supported beats, clarity pass, claim check, full prepared replies, owner-approved blog/HN titles, live repo/community links, and channel copy. | Post-ticket agent prepares; `nicktoper` approves and publishes. |
| Measurement tasks | Create `marketing/token-receipts` with its first suitable pairs and `marketing/phase-1-retro` with the baseline, scorecard, and dated 24-hour / 72-hour / day-14 checkpoints before post 1 ships. | `nicktoper` selects pairs and supplies private counters; assigned agents collect and score. |

Bookface is a hard pre-HN gate in `marketing/write-post`. If the owner reports
that it cannot be used, do not silently skip it: the owner must explicitly
change this plan and the skill's matching gate before any HN submission.

## Channel runbook

The blog is the canonical artifact. Attribution is deliberately
referrer-level: use the canonical blog URL everywhere, record publication
times, and read Jetpack referrers against the baseline. Do not buy analytics or
pretend newsletter-to-subscriber attribution is more precise than it is.

Use this order for every post:

1. **Day 0 — blog:** `nicktoper` publishes, then verifies the page, repo link,
   community link, and subscribe flow on the live URL.
2. **Day 0 — newsletter:** send only after the canonical page is verified.
3. **Day 0 — Bookface:** share the blog URL and collect the friendly read. Fix
   factual or structural problems on the canonical page before HN.
4. **Day 0 — optional X:** a summary may follow Bookface; omitting it never
   blocks the phase.
5. **Day +2 or +3 — HN:** submit from `top256` as a story, never Show HN,
   using an opponent-naming title. Pick a time when the founder can remain in
   the thread; account history gives no useful weekday or hour rule.
6. **The next day — Lobsters, when scheduled for that post:** submit from
   `ntoper`; do not split founder attention across the HN and Lobsters
   openings. Use `vibecoding` + `practices`, never `ai`, and only submit
   while the essay honestly reads as engineering practice.
7. **One day later — Reddit, only if eligible:** post from `Let047` to at
   most one relevant subreddit the founder already belongs to, check its
   current self-promotion rules, and write a native introduction. Never join a
   subreddit merely to drop the launch link.

On post 1 only, add a **fastjvm.com launch announcement** after the Day-0 blog
and newsletter are live. It is a one-time owner action, not a phase-1 channel,
not a gate, and not part of the short-term scorecard.

| Channel | Post 1 | Post 2 | Post 3 |
|---|---|---|---|
| Blog + newsletter | Required | Required | Required |
| Bookface before HN | Required | Required | Required |
| HN story | Required | Required | Required |
| Lobsters | Required | Use only if post 1 showed channel fit and this post still reads as engineering practice | Use unless post 1 established a clear channel mismatch |
| Reddit | Conditional on the joined-subreddit/rules gate | Conditional | Conditional |
| X | Optional | Optional | Optional |
| fastjvm.com | One launch announcement; unscored | No | No |

Never ask for upvotes. Sharing the article or thread is fine; let readers
decide what to do.

## Phase 1 — declutter launch and retro

Phase 1 starts only when all phase-0 gates are green. Ship post 1 through the
channel runbook and start the token-receipt ticket alongside it. The post agent
hands its channel timestamps and initial observations to
`marketing/phase-1-retro`; that separate ticket owns the 24-hour, 72-hour,
and day-14 checks so a writing ticket does not remain open as a hidden timer.
`nicktoper` supplies login-gated blog and community figures and makes the
phase disposition.

### Fixed phase-1 scorecard

These bars are set before publication. They diagnose different parts of the
launch; there is no post-hoc weighted score and installs are not substituted
for a miss.

| Signal | Bar by day 14 |
|---|---|
| HN | An observed front-page appearance and at least 30 points. Record placement while live; the API cannot prove it later. |
| Lobsters | At least 15 points and 5 comments. |
| Blog subscribers | At least +25 net from the pre-launch baseline. |
| Community | Discord: at least +15 members; GitHub Discussions: at least 15 unique non-owner participants or reactors. Either home also needs 3 people the owner did not already know posting something other than an introduction. |
| Vocabulary taking | At least one person the owner does not know uses "you are the CPU" or "batch your judgment" unprompted. |

Record stars, downloads, and installs as trailing context, not success bars.
The series is designed to spread an idea and recruit a narrow audience; it is
not an install campaign.

### Miss branches

- **HN dies in `/new`:** after the first attempt is clearly dead, email
  `hn@ycombinator.com` for the second-chance pool. If it is not lifted, make
  one resubmission no sooner than four days after the original, with a
  materially different opponent-naming title. Complete this branch before the
  phase-1 disposition.
- **HN hits but subscribers or community miss:** the essay reached people and
  the funnel failed. The post agent identifies the exact README, CTA, subscribe
  flow, or community-onboarding defect; the responsible ticket must be fixed
  before post 2 ships. Do not rewrite the thesis to explain a funnel miss.
- **Reach hits but vocabulary misses:** the idea did not transmit. Post 2's
  brief must explicitly sharpen the post-1-to-post-2 handoff, and the owner
  approves that change before publishing.
- **Lobsters misses its bar:** do not resubmit the same URL there. Treat the
  channel as unproven and omit it from post 2 unless the engineering-practice
  fit or account participation materially changes.
- **Both HN (after its retry) and Lobsters miss:** hold post 2's external
  launch for an owner decision on title/channel fit versus message fit. A miss
  does not make the finished essay unpublishable and does not automatically
  cancel the series, but it does remove automatic progression.

Post 2 may be drafted during the observation window. It does not publish until
day 14, the applicable branch work is closed, and `nicktoper` records a
proceed decision. Target publication within seven days of that decision so
post 1 can still recruit for it; an autonomy news cycle may choose the exact
day but must not hold the series indefinitely.

## Phase 2 — human amplification

Ship post 2 through the same channel runbook after the phase-1 owner gate.
Its specific content gate is a public, checkable correction-loop example with
both halves: the human's edit and the changed later behavior. The prepared
replies must include the real objection that keeping a human judgment gate is
less autonomous than managed alternatives; concede the trade rather than
renaming it as autonomy.

Continue token-receipt collection. Phase 2 is complete when its chosen channel
sequence is finished, responses and referrers are recorded, and at least four
valid receipt pairs exist. No new numeric audience threshold is invented here;
phase 1 is the pre-registered distribution test.

## Phase 3 — productivity mechanism

Post 3 waits for all of the following:

- post 2's channel sequence and response capture are complete;
- `marketing/token-receipts` holds at least four valid pairs;
- the evidence still supports the narrower documentation-as-cache mechanism;
- a selected pair and its exact cached question are copied or linked into the
  post-3 blackboard as working source support; and
- the post has cleared the ordinary `marketing/write-post` and owner gates.

If the receipt set is incomplete, postpone the post. If it contradicts the
premise, narrow or replace the claim rather than hiding the result. Once those
gates pass, ship through the channel runbook, targeted one to two weeks after
phase 2. The series ends at post 3; a proof post does not start automatically.

## Token-receipt protocol

`marketing/token-receipts` is a one-off agent-owned task created at phase-1
entry, not a recurring job and not new core code. During phases 1–2:

1. `nicktoper` selects 4–6 real implement-step tickets where the attached
   contexts plausibly contain task-relevant grounding.
2. For each, the agent makes a `<slug>-nocontext` copy with `contexts: []` on a
   throwaway branch and runs the real ticket with its contexts from the same
   starting revision, using the same model/agent where practical. Never rewind
   a task to manufacture the pair.
3. Before launch, save both `--prompt-report` outputs. Afterward, save
   `coga usage --task <slug> --json`, the usage-log reference, first-edit
   commit SHA/time, context refs, model, starting revision, and every material
   deviation between the runs.
4. Keep the receipt table on the token ticket's blackboard. Link or copy the
   selected rows into `marketing/post-doc-as-cache` when its brief starts.

A valid pair has the same task intent and starting revision, differs in ticket
contexts rather than repo context, and records any execution divergence. The
values remain source notes; they are never smuggled into post 3 as a result.

## Distribution tactics

- **Titles name an opponent.** This account's evidence reverses the old
  "experience, never thesis" rule. Every 30+ point story names something to
  disagree with — tech inevitability, the computing industry, Copilot, or VC —
  while descriptive, definitional, tutorial, and all six Show HN submissions
  scored 1–6 points. In the cleanest natural experiment, the same URL scored
  1 point as "Making All Software Faster: Experiments with Bytecode on
  Real-World Apps" and 32 four days later as "Computing Industry Doesn't Care
  about Performance: how I made things faster." Make the frame adversarial
  and the claim conservative.
- **Founder presence beats timing folklore.** The 26-story history does not
  distinguish weekday from weekend or one midday-Eastern slot from another.
  Submit when the founder can answer honestly and promptly.
- Quote the claim *genre* ("fully autonomous", "+500%"), never a competitor
  brand as an attack target.
- **Attribution without telemetry:** Jetpack referrers against publication
  timestamps and the pre-launch baseline, laid beside the GitHub-star and PyPI
  curves. Referrer-level attribution is enough; Coga never instruments users.
- **Craft risk is priced:** the founder has four 30+ point HN stories — 87,
  52, 47, and 32 — and three won on prose rather than a benchmark. The HN API
  records points, not placement, so never turn those scores into unobserved
  front-page claims.

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
  result, it graduates into the archived proof-post regime. Post 3's working
  receipts test and ground its mechanism; neither their values nor a measured
  outcome belongs in the essay. `marketing/write-post` step 6 enforces this.
- Misses stay publishable. Honest caveats and limits go in the posts, not in a
  FAQ, and a failed channel threshold is recorded rather than rationalized
  away.

## Ownership

| Role | Owns |
|---|---|
| `nicktoper` | Final message and phase decisions; login-gated facts and baselines; selecting receipt pairs; publishing/submitting through personal accounts; the fastjvm.com announcement; founder presence in threads. |
| Post-ticket agent | Source packet, brief, stress test, outline, draft, clarity pass, claim check, full replies, title/channel options, live-link verification, public metric capture, and blackboard handoff. |
| Cleanup/readme/community ticket assignees | Their named launch precondition, with evidence of completion in that ticket. |
| Token-receipt agent | Pair execution and the auditable receipt table; no public result claim. |
| Phase-1 retro agent | Public channel capture, checkpoint table, branch diagnosis, and a proposed disposition for the owner. |

External publication is an owner action. An agent prepares it and verifies the
result, but never infers permission to post from a completed draft.

## Execution tickets and disposition

- `marketing/phase-0-audit` — complete input to this plan; do not rerun it.
- Every ticket under `cleanup/` — blocking product/first-run queue.
- `marketing/readme-top` — blocking landing-page alignment.
- `marketing/discord` — blocking community-home decision and creation.
- `marketing/token-receipts` — create at phase-1 entry; collect 4–6 pairs
  through phases 1–2.
- `marketing/phase-1-retro` — create before post 1; own the dated checkpoints,
  HN second-chance branch, fixed scorecard, and owner disposition.
- `marketing/post-async-megalaunch` — **retained and rescoped** to post 1,
  mental decluttering. Async megalaunch is supporting detail; the stable slug
  is historical bookkeeping.
- `marketing/post-you-own-it` — **retained and rescoped** to post 2, human
  amplification. Ownership moves into the causal spine and post-1 trust beat;
  the stable slug is historical bookkeeping.
- `marketing/post-doc-as-cache` — **retained and sharpened** as post 3,
  productivity by mechanism. It does not publish receipt values or become the
  proof post.

None of the three post tickets is canceled. Each runs
`marketing/write-post`, which supplies the production steps and gates; this
context supplies the brief and launch state.

## Continuous — public responsiveness is the marketing

Answer issues and community questions quickly, fix docs when a reader
stumbles, and thank early testers. The public correction loop is the campaign
performed in real time. This is a standard to hold throughout all three
phases, not a fourth scheduled channel.

## What this context does NOT cover

- How a post is written and shipped — `marketing/write-post`, which hands its
  prose-craft pass to the imported `clarity` skill.
- Positioning, audience, voice, competitive facts, and honest product limits —
  `marketing/positioning`.
- The full strategy — `docs/market-thesis.md`; the why — `docs/vision.md`.
- The superseded experiment and proof-post machinery — archived in the
  unattached `marketing/launch-history` context, outside this composed plan.
