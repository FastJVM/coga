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

## Pitch 1 — measured human input, not claimed machine output

Every other launch in this field measures the **machine's output**
("fully autonomous," "+500% merged PRs," demo reels) and asks for trust.
This launch measures the **human's input** and offers proof: public
timestamps (log.md human events, human git commits, GitHub PR events),
blocker answers verbatim, and a metrics script anyone can rerun
(`scripts/human_minutes.py` — "recompute it yourself").

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

**"Not rocket science" is the pitch, not a confession.** The mechanism
is deliberately commodity — markdown, Python, git (the thesis doc: even
OpenAI open-sourced the same skeleton as Symphony). You could almost
build it yourself; that's the point — it's simple enough to *own and
understand*, and nothing hidden means nothing to pay rent for. This is
the independence/ownership spine (see `marketing/positioning`) in
economic form, and it converts the no-moat "weakness" into the offer.

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
  5 min).
- Small claims. Trust = recomputability + pre-registration + modesty.

## Sequence and dependencies

1. **Gates for the run:** `stabilize-megalaunch-for-daily-use` (the run
   starts when megalaunch holds up daily) and
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
5. **The post.**

## Success metric and tone

Success = **influence or a fan base**, not commercial dominance
(market-thesis). Default posture is fork A — an honest field report from
people running their own company on it — with fork B (Coga-as-category)
kept optionable. Write launch material as a field report unless the
human pins the fork otherwise.

## What this context does NOT cover

- Positioning, audience, voice, competitive framing, honest product
  limits — `marketing/positioning`.
- The full strategic argument — `docs/market-thesis.md`; the why —
  `docs/vision.md`.
- The experiment's exact measurement contract — the pre-registration doc
  and `metrics-human-minutes-script` ticket are authoritative.
