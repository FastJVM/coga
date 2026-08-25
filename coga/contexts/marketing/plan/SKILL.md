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
`v2/add-killer-demo`) were **deleted on 2026-08-19**; their text survives only
in this repo's git history (commits `9a93bff0` and `bedd29e2`). The machinery
they specified is *shelved for the later gated proof post* — the parts that
survive as tracked files are named under "Later, gated" below. The fork
question in `marketing/positioning` is pinned for this series: **fork A** — an
internal tool, open-sourced, told as a personal story.

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
- **Own the dogfooding, and source details beyond it.** Coga runs on
  itself and the post says so openly — the public repo is the passive
  receipt (the days the post describes are readable in git: log, tickets,
  PRs). The "coga working on coga" dismissal is preempted by drawing real
  details from non-Coga repos too (multiply, other team usage), so the
  story shows the practice, not the tool grooming itself.
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
- **Quickstart validated end-to-end** — same bucket as the README work:
  run the install/first-run path from the README on a fresh repo before
  the post ships. The internal-tool envelope lowers expectations, but a
  *broken* first run still burns every converted reader; this replaces the
  old plan's cold-start test at a fraction of its cost.
- **Community home, right-sized** (re-decided 2026-08-19): the post needs
  a "where to go" link before it ships, but an empty Discord is negative
  signal — the `marketing/discord` ticket decides between GitHub
  Discussions first (honest size, upgrade later) and Discord now; either
  must exist before post 1.
- **Token measurement assigned** — post 3 needs receipts collected during
  phases 1–2 (same task with vs without contexts; `--prompt-report`,
  schema-2 usage records). The audit names who/what collects them so
  phase 3 isn't blocked at writing time.
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
megalaunch holds up in daily use. What survives as tracked files, and where:

- **The metrics script** — `scripts/human_minutes.py` (covered by
  `tests/test_human_minutes_script.py`): human-attention episodes recomputed
  from public timestamps, with the measurement parameters pinned as constants
  (10-minute gap, 2-minute floor, 5-minute sensitivity floor).
- **Token accounting** — the same script's machine-token ledger, read from
  the schema-2 usage records.
- **The pre-registration commitment and its intention-to-treat inclusion
  rule** — `docs/velocity-report.md`, "Why there is no multiplier here": the
  pre-registered report "will count every attempt—completed, blocked,
  rescued, or abandoned—and link each row to its receipt."

Not preserved in any tracked file: the fallback framing (the what-broke field
report) and the demo brief exist only in the deleted tickets' git history, so
a future proof post has to re-decide them rather than pick them up. Do not
spend any of this apparatus on posts 1–3.

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
- **Craft risk is priced, not ignored:** the plan bets everything on the
  quality of the writing (no structural novelty backs it up), and that bet
  is on a demonstrated strength — the founder has front-paged HN twice on
  prose alone. Post 1 still gets iterations plus a Bookface read before HN.

## Prepared replies (comment-section discipline)

Write these out before post 1 ships; never improvise them in-thread:

- **"Show me / where are the receipts?"** — the repo is public; the days
  the post describes are readable in git (log, tickets, PRs). No numbers
  are claimed, but everything is passively verifiable.
- **"It's just markdown and a CLI — I'll build it myself."** — agreement,
  never defense: yes, that's why you can trust it. The value is the
  compounded substrate and the debugged discipline, not the mechanism; a
  homegrown version spends months re-learning it.
- **"How many PRs / how much did it actually ship?"** — no benchmark
  framing; the post claims a practice, not a result. Point at the repo;
  the proof post, if it ever runs, is the numbers play.
- **"You're just running it on itself."** — dogfooding is stated in the
  post itself, alongside non-Coga usage details; the practice is the
  claim, and the repo running on it is the standing demo.

## Claim discipline (adapted for the essay series)

- Descriptive claims only; **no productivity multiplier anywhere**. Coga has
  never published a multiplier figure and must not start: the surviving claim
  is the two-person/output-of-ten bet in `docs/vision.md` ("The thesis"),
  stated as a bet and never as a result, and `docs/velocity-report.md` holds
  that line in public ("this report makes no '5x,' '10x,' or percentage
  productivity claim").
- Essay posts claim *ideas*, not results — so they carry no numbers and
  need no receipts. The moment a post states a figure as a result, it
  graduates into the proof-post regime (pre-registration, recomputability)
  — don't drift there by accident.
- Misses stay publishable: the "takes time to feel" caveat and honest
  limits (see positioning) go *in* the posts, not in a FAQ.

## Success metric

Phase 1–3 are scored on **influence and audience**: the idea circulating
(the vocabulary taking — "you are the CPU", "batch your judgment"), blog
subscribers, joins and participation on whatever community home
`marketing/discord` selects (GitHub Discussions or Discord — still undecided;
see phase 0), stars/downloads as trailing proxies. Installs
remain the long-arc goal but are *not* the bar for the essay posts — by
construction they convert lightly. The proof post, if it ever runs, is the
installs play.

## Execution tickets (created 2026-08-19)

- `marketing/phase-0-audit` — the audit above (includes the quickstart
  run-through and the token-measurement assignment); output is the
  worklist.
- `marketing/readme-top` — align the README top with the story.
- `marketing/discord` — right-size and create the community home (before
  post 1; Discussions-vs-Discord decided in the ticket).
- `marketing/post-async-megalaunch` — write post 1 (structure above).
- `marketing/post-you-own-it` — write post 2 (phase 2 angle rules).
- `marketing/post-doc-as-cache` — write post 3 (needs the collected
  measurements).

## What this context does NOT cover

- Positioning, audience, voice, competitive framing, honest product
  limits — `marketing/positioning`.
- The full strategic argument — `docs/market-thesis.md`; the why —
  `docs/vision.md`.
- The old experiment's measurement contract — shelved with the proof post;
  the superseded plan text lives in git history of this file.
