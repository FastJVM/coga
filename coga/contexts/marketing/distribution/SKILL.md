---
name: marketing/distribution
description: Coga launch channels, dated account evidence, attribution, amplification asks, audience scorecard, and response branches. Read when preparing distribution or scoring a launch.
---

# Coga distribution

This is the authored home for channel facts and launch distribution policy.
`marketing/plan` owns the launch deliverables and phase gates;
`marketing/write-post` owns the publishing checks. Publication and personal
account actions belong to `nicktoper`.

## Recorded surfaces and outstanding facts

Extracted from the phase-0 audit on 2026-09-09. Public observations below were
recorded on **2026-09-02/03**; they are dated evidence, not a fresh check of a
site, account, or community rule. Recheck applicable live rules and links
before submission. Sources: [audit evidence](../../../tasks/marketing/phase-0-audit/step-1-findings.md)
and [owner decisions](../../../tasks/marketing/phase-0-audit/audit-history.md).

| Surface | Recorded evidence | Still needed for launch |
|---|---|---|
| [Blog](https://deviantabstraction.com) | WordPress/Jetpack, email signup present; latest post then was 2026-06-02. No Coga mention found in that audit. | Subscriber count, trailing-30-day views, and a completed real subscribe test. |
| [HN account](https://hacker-news.firebaseio.com/v0/user/top256.json) | `top256`, joined 2016, karma 213 as confirmed 2026-09-03. The audited history is 26 stories; own essays and active replies when a story draws discussion. | Founder-present submission window and owner-approved title. |
| [Lobsters account](https://lobste.rs/u/ntoper) | `ntoper`, created 2025-06-05; karma 55. One self-authored blog submission scored 26 points / 19 comments. | Current tag/fit check. The audited tags were `vibecoding` + `practices`, never `ai`; the essay must read as engineering practice. |
| [Reddit account](https://www.reddit.com/user/Let047/) | Owner reported 7,781 karma, 2,609 contributions, six years, 56 followers. Unauthenticated fetches were blocked. | Joined-subreddit list and current self-promotion rules for at most one suitable existing community; omit Reddit if none fits. |
| Bookface | Login-gated; standing and feasibility remain unreported. | Owner confirms it can be used before HN. Unavailability requires an explicit change to the plan and writing skill's matching gate. |
| [fastjvm.com](https://fastjvm.com) | Audit found a JVM research index, without a natural Coga link slot. Owner chose a one-time launch announcement anyway. | Owner publishes after the Day-0 blog/newsletter; it is unscored and never a blocker. |
| Community home | Audit found no home: GitHub Discussions disabled, no Discord link. `marketing/discord` remains the decision/implementation ticket. | Choose and create the home, link the exact URL, test that someone can ask a real question, and record its baseline. |

The newsletter is the blog's subscription channel. Referrer reports support
coarse traffic attribution; email clients may suppress referrers. Do not
claim that Jetpack identifies the channel responsible for an individual
subscription.

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
| Launch YC | No | One product launch, placed during launch planning; unscored | No |
| YC amplification | No | Rides the Launch YC announcement; unscored | No |
| Friends share ask | Optional; unscored | Optional | Optional |
| fastjvm.com | One launch announcement; unscored | No | No |

Never ask for upvotes. Sharing the article or thread is fine; let readers
decide what to do.

## YC channels and personal asks

Coga is YC-backed, so `nicktoper` has two distribution moves the essay channels
above do not cover. Both are **product-launch shaped**, and that is the tension
to hold: `marketing/plan`'s play states the series is deliberately not a product
announcement. They are owner actions on their own schedule, not steps a post
agent slots into post 1's Day-0 sequence.

- **Launch YC.** Publish a product launch on Launch YC — its own surface, page,
  and audience. It is alumni-gated, so it rests on the same unreported Bookface
  standing the pre-HN read does. Write it to the series' own envelope — *this is
  my internal tool; I'm open-sourcing it* — pointing at the repo and the
  install, not at an essay's thesis.
- **YC amplification.** Ask YC to amplify that launch announcement from its own
  accounts. It attaches to the product launch, not to an essay, so the optional
  Day-0 X summary is not its prerequisite and skipping X does not remove it.
- **Friends.** Ask people the owner actually knows to share the canonical blog
  URL or a live thread. Personal and one-time.

Three constraints hold whenever they fire:

- **Keep them out of the HN window.** Days 0 to +3 already commit the founder to
  the Bookface read and a live HN thread, and the runbook's own rule is not to
  split founder attention across two openings. The product launch sits after
  phase 1's day-14 disposition, and the same rule applies inside post 2's own
  window.
- **Unscored, and excluded from the phase-1 read.** No scorecard bar depends on
  them and silence is not a miss branch. They move stars, PyPI downloads, and
  referrers — which the scorecard already treats as trailing context — so record
  the exact date each one fires, or a product-launch spike gets read as the
  essay's audience response.
- The boundary above is unchanged: ask for a share, never for a vote, and never
  assemble friends or the YC network into voting on HN, Lobsters, or Reddit.

**Owner decision, 2026-09-09:** the product launch runs **after phase 1**, with
the second run of the series. It does not open the campaign. The exact placement
against post 2's window is tailored during launch planning
(`marketing/build-the-launch-plan`), so no ticket should fix a date for it here.

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

## Fixed phase-1 scorecard

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

## Miss branches

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

## Continuous — public responsiveness is the marketing

Answer issues and community questions quickly, fix docs when a reader
stumbles, and thank early testers. The public correction loop is the campaign
performed in real time. This is a standard to hold throughout all three
phases, not a fourth scheduled channel.

## Measurement boundary

Audience response remains useful to this launch: reach, subscribers, community
participation, and whether the vocabulary travels. Before publication, record
the subscriber, trailing-30-day views, community, GitHub-star and PyPI-download
baselines, plus the subscribe-flow test. The planned
`marketing/phase-1-retro` ticket owns dated checkpoints and the owner's
disposition.

The owner removed paired token/time measurements from the launch on
2026-09-09. No token experiment, receipt quota, or token-success bar is required.
The historical protocol is in `marketing/launch-history`; ordinary operational
usage records and prompt-size diagnostics are separate from campaign success.
