---
name: marketing/plan
description: The Coga launch plan — a series of personal essays on the founder's blog, starting with the "async megalaunch" story. Attach to any marketing/comms ticket alongside marketing/positioning. Positioning says what's true about Coga's market position; this says what we're doing, in what order, and under what rules.
---

# Coga marketing plan

The operational plan for Coga's launch. When this drifts from
`marketing/positioning` or `docs/market-thesis.md`, they win — update this
file in the same change.

**Status (2026-08-19): this plan supersedes the "20 minutes a day"
experiment program entirely** (decided by the owner, 2026-08-18/19). The old
plan led with a pre-registered 2-week run and a measured result; it was
gated on megalaunch stability, held its hook hostage to an unknown N, and
buried the message under the apparatus. The new plan leads with the idea and
defers every proof. The old program's tickets (`v2/launch-20-minutes-a-day`,
`v2/add-killer-demo`) describe the superseded plan; their machinery
(pre-registration, metrics script, demo) is *shelved for the later gated
proof post*, not deleted — see "Later, gated" below. The fork question in
`marketing/positioning` is pinned for this series: **fork A** — an internal
tool, open-sourced, told as a personal story.

## The play: a series of personal essays

The launch is **not** a product announcement and **not** a public
experiment. It is a series of first-person essays on the founder's personal
blog, each carrying exactly one idea, each recruiting readers for the next.
The envelope for the whole series: **"this is my internal tool; I'm
open-sourcing it."** That framing is structurally unattackable (an internal
tool shared has no missing features, only rough edges that are part of the
contract) and matches fork A exactly.

The genre is the **idea essay that names a felt pain** (the local-first /
choose-boring-technology lineage): the target reader verifies the thesis
against their own life, so the post needs recognition and imaginability,
**not proof**. No ledger, no metrics, no demo required. The discipline that
replaces receipts: real concrete detail (the actual morning gesture, the
actual questions in the queue) — an idea essay written in generalities is
worthless; written with true specifics it converts.

## Post 1 — "async megalaunch" (the story)

The founder's story, told **in the present tense, never as genesis** (the
repo's public history shows the real genealogy started from principles, not
this problem — claiming otherwise hands skeptics a free gotcha; the
present-tense version is equally strong and fully true).

The arc, five beats:

1. **The problem, present tense** — founder of a small company, needs to
   maximize productivity, doesn't have time to waste; the chained state
   (terminal tabs, each agent session blocking on him, context-switching
   all day — *you are the CPU*).
2. **Requirement 1: it works without me** — the morning gesture: answer
   the accumulated question queue, review, brief tickets, launch the sweep
   (megalaunch), close the laptop. "You launch the wave and you leave."
3. **Requirement 2: but I see where it's going** — no black box; agents
   that hit a real decision queue their question instead of guessing;
   everything is files in my git; I steer *before* rather than re-correct
   *after*. This double requirement (leave AND see) is the story's engine
   and the one nobody else in the category can tell — autonomy tools
   liberate by blinding you; supervision keeps you seeing by keeping you
   chained. Coga refused the trade.
4. **What it became** — ultra simple by choice: markdown, git, a CLI. A
   real day narrated with real details.
5. **I'm open-sourcing it** — one line, the repo link, the honest caveat
   ("the first days feel like setup; the payoff arrives when the loop
   closes, then compounds"), no pitch.

Writing rules for this post (and defaults for the series):

- One post, one idea. Everything else is a later post.
- Present tense, real details, first person.
- **No numbers as claims.** The claim is the *shape of the day*
  ("an hour or two in the morning, then I leave"), never a figure that
  invites verification. An essay claims ideas, not results.
- The complicated ideas (Pirsig, compile-your-company, operations-as-code,
  the manifesto register) stay out — they are later posts, aimed at the
  audience this one creates.
- The documentation/token pitch stays out (it's post 3).

## The phases

**Phase 0 — audit and prep (before publishing anything).**

- **Audit what exists vs what's needed** — first action of the plan:
  inventory the README (does its top tell the post's story?), the blog and
  newsletter, the state of megalaunch and the blocker queue as *narrative
  material* (real examples to quote), the community surfaces, and the old
  marketing tickets' disposition. Output: the concrete phase-0 worklist.
- **README top aligned with the story.** Every convinced reader clicks the
  repo link; the README is the landing page. Not a full rewrite — the top
  must echo the post (what it is, for whom, the day-shape).
- **Discord re-created** (decided 2026-08-19; the canceled
  `marketing/relay-discord` is re-filed). Must exist *before* post 1 ships
  — it is the "where to go" link, and spike readers are not recoverable
  after the fact.
- **Measurement thresholds noted** before publishing (privately is fine) —
  so the phase-1 retro can't be post-hoc rationalization.

**Phase 1 — post 1, "async megalaunch".**
Blog is the canonical hub; distinct per-channel URLs. Newsletter day 0.
Bookface a few days *before* HN (friendly fire hardens the post; YC readers
arrive in the HN thread already convinced). HN as a plain-titled **story
submission only** — never Show HN. X optional: one summary thread.
Reddit deferred (self-promo economics are bad cold; post only where already
a member, or leave for phase 2+).

**Phase 2 — post 2, "you own it".**
Ownership / control / simplicity — **by specifics, never as humanist
slogan** (the "keep thinking" space is occupied by Anthropic and the echo
reads as ours; see positioning's slogan rule). The defensible angle: *in
your repo, not their cloud; you can read everything the system did;
vendor-neutral; zero telemetry; flat cost.* Include the prepared
**"just markdown" judo**: yes — it's simple enough to own and understand,
that's exactly why you can trust it; nothing hidden means nothing to rent.
This post answers the question post 1 raises ("why would I trust my days
to this?"): you trust nothing — everything is yours and legible.
Timeable: hold it for the next autonomy-hype cycle and publish as the
counter.

**Phase 3 — post 3, "documentation as cache".**
The token-reduction/speed pitch: sessions are stateless, so an undocumented
repo makes the agent re-buy the same understanding every run; contexts are
that understanding bought once and composed into every prompt for free —
documentation stops being hygiene and becomes a cache, and it's why you can
walk away. This post *benefits from receipts* (same task with vs without
contexts: tokens, time-to-first-edit; `--prompt-report` + schema-2 usage
records), which is why it comes after the audience exists — collect the
measurements during phases 1–2.

**Later, gated — the proof post.**
The 2-week pre-registered experiment ("N merged PRs, the ledger, recompute
it yourself") survives as an *option*, run only if the series lands and
megalaunch holds up in daily use. All the old plan's machinery is preserved
for it: pre-registration git-dated before data, intention-to-treat
inclusion, the metrics script, token accounting, the fallback framing
decided before the run (what-broke field report — possibly the best HN
title of all). Do not spend any of this apparatus on posts 1–3.

**Continuous — public responsiveness is the marketing.**
For an OSS repo, visible reactivity *is* the campaign: answer issues fast,
fix docs when someone stumbles (the correction loop, performed in public),
thank early testers. Nothing to schedule; a standard to hold.

## Distribution tactics (kept from the old plan — still valid)

- **HN failure branch:** if the submission dies in /new, mail
  hn@ycombinator.com (second-chance pool), then resubmit after a decent
  interval. **Never solicit upvotes** — share the link, let people act.
- Weekday morning US for HN; founder present in the thread.
- **Titles are the experience, never the thesis** — a thesis title gets
  argued before it gets read. The thesis opens paragraph one.
- Quote the claim *genre* ("fully autonomous", "+500%"), never the brand.
- **Attribution without telemetry:** per-channel URLs into the blog
  (first-party analytics), laid against PyPI download curve and GitHub
  star timeline vs post timestamps. Phase decisions get made from this.

## Claim discipline (adapted for the essay series)

- Descriptive claims only; **no productivity multiplier anywhere**; the 5x
  stays in `docs/vision.md` as a stated bet, never a result.
- Essay posts claim *ideas*, not results — so they carry no numbers and
  need no receipts. The moment a post states a figure as a result, it
  graduates into the proof-post regime (pre-registration, recomputability)
  — don't drift there by accident.
- Misses stay publishable: the "takes time to feel" caveat and honest
  limits (see positioning) go *in* the posts, not in a FAQ.

## Success metric

Phase 1–3 are scored on **influence and audience**: the idea circulating
(the vocabulary taking — "you are the CPU", "batch your judgment"), blog
subscribers, Discord joins, stars/downloads as trailing proxies. Installs
remain the long-arc goal but are *not* the bar for the essay posts — by
construction they convert lightly. The proof post, if it ever runs, is the
installs play.

## Tickets to (re)create

Re-derive execution tickets from this file (the old refs are superseded):

- `marketing/phase-0-audit` — the audit above; output is the worklist.
- `marketing/readme-top` — align the README top with the story.
- `marketing/discord` — re-create the community home (before post 1).
- `marketing/post-async-megalaunch` — write post 1 (structure above).
- `marketing/post-you-own-it` — write post 2 (phase 2 angle rules).
- Later: `marketing/post-doc-as-cache` (+ its measurement collection).

## What this context does NOT cover

- Positioning, audience, voice, competitive framing, honest product
  limits — `marketing/positioning`.
- The full strategic argument — `docs/market-thesis.md`; the why —
  `docs/vision.md`.
- The old experiment's measurement contract — shelved with the proof post;
  the superseded plan text lives in git history of this file.
