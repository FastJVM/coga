---
name: marketing/plan
description: The Coga launch plan — the "20 minutes a day" demonstration, its two pitches, claim discipline, and the ticket sequence behind it. Attach to any marketing/comms ticket alongside marketing/positioning. Positioning says what's true about Coga's market position; this says what we're doing, in what order, and under what claim rules.
---

# Coga marketing plan

The operational plan for Coga's launch. Source tickets:
`marketing/launch-20-minutes-a-day`, `metrics-human-minutes-script`,
`marketing/rewrite-readme-around-the-wedge`, `marketing/add-killer-demo`,
`marketing/relay-discord`. When this drifts from those tickets or from
`docs/market-thesis.md`, they win — update this file in the same change.

## The play: a demonstration disguised as a report

The launch is **not** a product announcement. It is a 2-week public
experiment — megalaunch drains the real backlog, the founder's entire
human contribution is ~20 min/day (blocker queue + reviews) — followed by
a post built strictly on its data: *"Two weeks. Twenty minutes a day.
N shipped tasks."*

We never say "Coga is great." We say "here's what happened, here's the
ledger, check our math" — and Coga is simply the visible machinery in
every row. Coga is offered as **proof that the practice works**
(operations-as-code with human judgment as the only human input), not as
a claim about itself. The pitch is nearly implicit: if you want this
practice, the machinery that produced the ledger you just audited is in
the same repo, free.

This works only because the whole operation runs in a public repo that
records itself — the marketing claim is a consequence of the
architecture (legible, git-backed, nothing hidden). That is why no
competitor can run the same play without becoming the same product.

## The hook — rules and known risks

Headline hook: *"Two weeks. Twenty minutes a day. N shipped tasks."*
Three beats, numbers-forward, falsifiable, story-shaped (a fortnight of
someone's life, not a feature list). It generates the "wait, how?"
curiosity gap. Rules that keep it working:

- **The hook holds a hostage: N.** Its power depends on a number we
  don't have until the run ends. Decide the fallback framing **before**
  the run (pre-registration spirit): if N disappoints, the post becomes
  the honest what-broke field report — failure reports also travel.
  Deciding the frame after seeing the data is the one move that breaks
  the whole trust story.
- **Make N concrete fast.** "Tasks" is internal vocabulary a skeptic
  reads as padding — in the post, resolve N to PRs, artifacts, and links
  within the first screen.
- The hook names no category and no product — good for curiosity, bad
  for recall. **The subtitle must carry the brand** and one fact only we
  can say (your git / flat cost).
- **Slogan rule:** "Agents do. Humans think." collides with Anthropic's
  "Keep thinking" — in a feed, *we* read as the echo, because they own
  the megaphone. Keep the line, but any headline placement must pair it
  immediately with a note Anthropic can't sing: ownership/independence
  ("…on a machine you own", "in your repo, not their cloud"). Never let
  the humans-think note stand alone as the positioning.
- **Post structure — the identification beat is mandatory:** hook →
  **wedge** ("you already run agent sessions as terminal tabs; you're
  the CPU — become the I/O device answering batched interrupts") →
  experiment/proof → pitch 2 (cost/ownership) → install. The wedge names
  the reader's felt pain today; the autonomy argument alone is abstract
  and the experiment alone is about us, not them.
- **First person, recipe-shaped.** The voice is "I" — a founder's field
  report — never "we announce." No solved-hot-water claims anywhere: the
  posture is *show the result, hand over the method*. The closing beat
  is **"here's how I did it"** — the exact setup, commands, tickets, and
  morning ritual, detailed enough to replicate the fortnight. This is
  the conversion engine: a report gets read, a recipe gets run, and
  replication is the install path. The attitude cuts only because of
  what's underneath it — humble in tone, arrogant in specificity,
  provocative in verifiability.

## Pitch 1 — measured human input, not claimed machine output

Every other launch in this field measures the **machine's output**
("fully autonomous," "+500% merged PRs," demo reels) and asks for trust.
This launch measures the **human's input** and offers proof: public
timestamps (log.md human events, human git commits, GitHub PR events),
blocker answers verbatim, and a metrics script anyone can rerun
(`scripts/human_minutes.py` — "recompute it yourself").

The script's default is the complete ledger, not a best-effort scrape: it reads
`coga/log.md`, follows each ticket's recorded `pr:` through `gh`, excludes Coga
state-sync commits, and fails loud when GitHub data cannot be read. Explicit
`--no-github` / `--no-git` flags exist for visibly partial offline analysis.
Run it with the pre-registered date window and timezone; `--json` is the stable
machine-readable receipt. The per-day total clusters all attributed events
together (so overlapping task work is not double-counted), while the per-task
rows cluster each task independently.

The anchor argument (goes in the post verbatim, in substance): **there
is no such thing as full autonomy** — autonomy is a function of spec
quality + evaluability. The 20 min/day is the irreducible
spec-and-judgment work no model upgrade removes; Coga is the machinery
that makes 20 minutes of it enough. Zero-minute claims are lies of
omission: they hide the spec-writing, review, and babysitting — or hide
slop. Twenty minutes is the honest floor everyone has and nobody
reports.

Why this beats the field (the Devin trap): inflated launch claims get
publicly debunked and never recover with our tribe. Our audience is
selected for being exhausted by inflated claims — the crowded stampede
of "autonomous" launches is exactly what makes a pre-registered,
recomputable, misses-published claim legible. In a quiet field modesty
is invisible; in this one it's a signal.

Known weaknesses — acknowledge, don't paper over:

- Skeptics attack **N**, not the 20 ("small tasks, coga working on
  coga"). Mitigation: receipts per row, artifact links, the what-broke
  section, field-report framing (never benchmark framing).
- The claim **refuses head-to-head comparison** and therefore can't win
  one. Never say "better than Devin"; it's a claim about a working
  practice, not model capability.
- **Prepared answer to "but Devin/Symphony do this with zero human
  minutes":** we are not entering the autonomy race, so we can't be
  outclassed in it. They sell *self-magic* and measure machine output;
  this experiment measures **leverage per human minute** — an axis
  where nobody else has a number at all. It's not self-magic: it's
  20 minutes a day buys you magic. Deliver this as numbers (theirs
  unverifiable, ours recomputable), not as a values argument.
- It wins the second read, not the headline scan. This launch will not
  go wide, by design — consistent with the narrow-tribe strategy.

## Pitch 2 — the deeper cut: open source, flat cost, not rocket science

Lands after the reader has audited the ledger: everything you just
verified was produced by **open-source software riding flat
subscriptions — nothing metered, no per-seat platform, no enterprise
sales call.** State the flat cost line and let the reader do the
division ($/mo ÷ N tasks) — never do it for them. (The launch ticket
currently says "two subscriptions, ~$400/mo" — claude + codex rotation;
use the actual count and figure from the run.)

**Cost with receipts (token accounting).** The run captures machine-side
token usage (autonomous vs interactive). The post reports: tokens
consumed → what that costs at API prices → what it actually cost on
flat subscriptions. This turns the cost line from defense into offense —
the division stops being "$X per task" (attackable if tasks read small)
and becomes "$X bought this many tokens of machine labor, metered that's
$Y." We run every division ourselves before inviting the reader to.

Capture is already part of the public ledger: schema-2 `[system]` usage records
in `coga/log.md` carry provider/model token buckets and transcript-derived
`human_turns`. `scripts/human_minutes.py` groups `human_turns == 0` as
autonomous, `human_turns > 0` as interactive, and missing turn data as unknown;
unknown sessions stay visible rather than being guessed away. API-equivalent
pricing is applied to the script's per-provider/model token buckets using prices
locked for the run, not hard-coded into the timeless capture format.

**"Not rocket science" is the pitch, not a confession.** The mechanism
is deliberately commodity — markdown, Python, git (the thesis doc: even
OpenAI open-sourced the same skeleton as Symphony). You could almost
build it yourself; that's the point — it's simple enough to *own and
understand*, and nothing hidden means nothing to pay rent for. This is
the independence/ownership spine (see `marketing/positioning`) in
economic form, and it converts the no-moat "weakness" into the offer.

**Prepare the "just markdown" judo.** The simplicity pitch invites the
predictable dismissal: *"so it's markdown files and a CLI — I'll build
it myself with Claude Code."* The prepared reply is agreement, never
defensiveness: *yes — that's why you can trust it.* The value isn't the
mechanism; it's the compounded substrate and the discipline, already
built and debugged, that a homegrown version spends six months
re-learning. Bake this into any copy that leans on simplicity.

## Noise strategy — winning attention we can't buy

Judged as raw noise, we lose every contest: rivals have bigger claims
(Devin "the first AI software engineer", Viktor "a hire, not a tool"),
bigger megaphones (Symphony's "+500% merged PRs" with OpenAI's
distribution, Anthropic's "Keep thinking"), or a more famous voice
(CompanyOS = Brad Feld). The plan does not try to out-shout. Instead:

- **Counter-position against the claim genre.** The anchor sentence
  ("there is no such thing as full autonomy") attacks the entire field's
  launch claims at once — and counter-positioning rides distribution the
  big players paid for. Every future "fully autonomous" launch spike is
  a moment our pre-registered ledger is the standing rebuttal someone
  links in the comments.
- **Ride the wave, don't dodge it.** Time the pre-registration
  announcement to land as *the reply* to the next autonomy-hype cycle,
  not in a quiet week. In a quiet field modesty is invisible; in a loud
  one it's a signal.
- **Own the metric, not just the number.** Symphony owns "+500% PRs";
  nobody owns **human-minutes per shipped task** — absolute,
  human-scaled, recomputable. Introduce it in the post *as a named
  metric*, not merely as our result. Strategic kicker: computing it
  requires a legible, self-recording substrate — if the metric spreads
  ("what's your human-minutes?"), answering it pushes people toward
  Coga-shaped record-keeping. This is the influence-win made concrete.
- **Quote the genre, never the brand.** Cite "+500%" and "fully
  autonomous" as claim *shapes*, without naming Devin/Symphony/anyone.
  Naming makes us the aggressor and summons their fans; leaving the
  blank makes the comment section fill it in — more noise, none of the
  blame.
- **Pick skeptic-dense channels.** The hook wins where verifiability and
  contrarianism outperform budget (HN, dev social); it loses the
  headline-scan war in mass channels by design. Inviting the audit
  ("check our math") is itself the engagement mechanic there.
- **Nearest-neighbor hazard:** against CompanyOS ("Feld's markdown
  company") we lose on recall if the framings blur. The differentiator
  to foreground is exactly what he doesn't have: the ledger and the
  human-gated loop — the experiment *is* that difference, demonstrated.

## Claim discipline (applies to ALL Coga comms, not just the post)

- Descriptive claims only. **No productivity multiplier anywhere** — the
  5x stays in `docs/vision.md` as a stated *bet*, never a result.
- Every number recomputable from the public repo; prefer server-held
  timestamps (GitHub) that can't be locally backdated.
- Misses published: inclusion is intention-to-treat — every task
  megalaunch *attempts* is reported (completed / blocked / rescued /
  abandoned).
- Pre-registration is git-dated **before any data**: window, inclusion
  rule, measurement method (10-min gap, 2-min floor, sensitivity at
  5 min) — plus the four locks below.
- Small claims. Trust = recomputability + pre-registration + modesty.

**The pre-registration commit must also lock (closes the audit holes):**

- **Tool-repair rule.** Stabilization precedes the window — that is what
  the megalaunch gate *means*. If the tool still breaks mid-run, repair
  time is reported **separately** from the operating figure, never
  silently excluded and never blended into the 20. The window measures
  *operating the company*, not *building the tool*, and the split is
  disclosed so no skeptic discovers it.
- **Attention scope.** Declare the actual practice: there is no ambient
  monitoring — no standing Slack-feed watch; human attention happens in
  the logged episodes (blocker queue + reviews). Stated up front so the
  "but you're ambiently supervising all day" attack has a pre-dated
  answer.
- **Backlog snapshot + task-sizing rule.** The backlog is snapshotted
  and the granularity rule fixed in the same commit, so N cannot be
  inflated (even unconsciously) by splitting tickets finer mid-run.
- **Token accounting.** Machine-side token usage is captured for the
  run (autonomous vs interactive), so the cost line ships with
  receipts: tokens consumed → API-equivalent price → actual flat
  subscription cost. Run the division ourselves before inviting it.

## Sequence and dependencies

1. **Gates for the run:** megalaunch stable in daily use (the run starts
   when megalaunch holds up daily — proven empirically, with narrow fix
   tickets filed as failures surface; the former
   `stabilize-megalaunch-for-daily-use` ticket was folded into this) and
   `metrics-human-minutes-script` (the recompute story).
2. **Pre-registration commit** — one commit, before any data.
3. **The 2-week run** — megalaunch as default work mode; daily diary is
   derived from the log by the metrics script, never hand-written.
4. **Landing surface**, ready before the post ships:
   `marketing/rewrite-readme-around-the-wedge` (README the post points
   at, "Agents do. Humans think."), `marketing/add-killer-demo` (60-sec
   morning-ritual demo embedded in README + post), and
   `marketing/relay-discord` — the **open decision** (Discord vs public
   Slack) must land first; the post needs a "where to go" link.
5. **Cold-start test (gate before the post ships).** One outsider — a
   Bookface founder is the obvious pick — installs Coga from the README
   unaided, on their own repo, and reaches the correction-loop moment.
   Their time-to-first-value is published in the post. This is the only
   step that verifies the install funnel before a crowd is pointed at
   it, and it converts "here's how I did it" from a demo of the
   founder's private substrate into evidence a reader can act on.
6. **The post.**

## Distribution — phase 1 (decided 2026-07-15)

Three channels, one of each kind — a public spike (HN), an owned
audience (blog/newsletter), and a high-trust private room (Bookface).
Same dataset, a distinct framing per channel. Realistic bet: BF +
newsletter + HN together get the first users; nothing here is counted
on to go wide. (Fuller distribution & conversion work is a later
ticket; this is the decided phase-1 scope.)

**Sequencing (deliberate):**

1. **The pre-registration is itself the first launch (spike one).**
   Not newsletter-only: it goes to HN too, as its own story — "I
   pre-registered my launch like a clinical trial; locked methodology,
   public repo, watch it live." A genre HN hasn't seen, undebunkable
   by construction (no results yet — only methodology, and methodology
   critique in the comments is free peer review). It converts
   spectators into stakeholders with a two-week open loop, and the
   public repo doubles as a live demo for the duration. This is also
   the wave-riding venue: the announcement is *timeable* — hold it for
   the next autonomy-hype moment and post it as the counter. The
   newsletter (~300 subs, realistically ~120 readers) gets it first or
   same-day; they're the serialized audience with stakes, not an
   amplifier. Announce only once the megalaunch gate is already met —
   the announcement trails the gate, never leads it.
2. **Bookface, a few days before HN.** Lower-variance than HN and the
   exact buyer (small team, wants leverage, tolerates rough edges).
   Founder framing: "how I run my company in 20 min/day." Two jobs:
   friendly-fire feedback that hardens the post before skeptics see
   it, and YC founders who arrive in the HN thread already convinced.
   Private — nothing there is publicly quotable. Early YC adopters
   become phase-2 credibility.
3. **HN — the results post (spike two), as a story submission ONLY.**
   The field report ("here's how I did it"), never a Show HN / product
   submission — product submissions are a lottery; the story is the
   asset. Plain title, no marketing language, weekday morning US.
   Founder has front-paged HN before: execution (title, timing,
   presence) beats the base rate. Be present in the thread answering
   skeptics with ledger links — the comment section is where "check
   our math" pays off. Spike two lands on the audience spike one
   recruited; the added stake — a public spike one means a mediocre
   fortnight fails in front of an audience — is priced in: the
   fallback framing (what-broke field report) covers it, and the
   exposure IS the credibility mechanism.

**HN failure branch (decide nothing on the day):** if the submission
dies in /new, use the second-chance pool (a polite mail to
hn@ycombinator.com re-ups good field reports surprisingly often), then
resubmission after a decent interval. **Never solicit upvotes** from
the newsletter or anywhere — vote-ring detection buries posts; share
the link, let people act.

**The blog is the hub.** The canonical post lives on the founder's
blog; every channel points at it, so even a modest spike converts into
subscribers and a permanent, linkable artifact.

**Attribution without telemetry.** Coga never phones home (principles);
attribution is external: distinct per-channel URLs into the blog
(first-party analytics only), laid against public proxies — the PyPI
download curve (pypistats) and the GitHub star timeline vs post
timestamps. Phase 2 channel decisions get made from this, not vibes.

**Pre-register distribution expectations too.** Before launch, write
success thresholds into the pre-registration commit (front-page vs
died-in-new; star/download/install-proxy targets) with the phase-2
consequence of each scenario — so the retro can't be post-hoc
rationalization.

Deliberately out of phase 1: X/dev-social, Product Hunt, reddit — later
ticket, if at all. The ride-the-hype-wave tactic has its phase-1 venue
in spike one (the timeable pre-registration announcement); sustained
wave-riding between spikes still has no venue until X exists.

## Success metric and tone

**The goal of this launch is installations** (decided 2026-07-15,
overriding the earlier influence-first framing). Influence and the fan
base are the *mechanism*, not the metric: the ideas spreading is how
installs happen, but success is counted in people running `coga init`
on real repos — measured by public proxies (PyPI download curve, star
timeline, community-channel joins), with the target number pinned in
the pre-registration commit alongside the distribution thresholds.
The market-thesis influence/fan-base framing remains the *long-arc*
metric; this launch is scored on installs.

Tone is unchanged: fork A — an honest field report from people running
their own company on it — with fork B (Coga-as-category) kept
optionable. Write launch material as a field report unless the human
pins the fork otherwise.

## What this context does NOT cover

- Positioning, audience, voice, competitive framing, honest product
  limits — `marketing/positioning`.
- The full strategic argument — `docs/market-thesis.md`; the why —
  `docs/vision.md`.
- The experiment's exact measurement contract — the pre-registration doc
  and `metrics-human-minutes-script` ticket are authoritative.
