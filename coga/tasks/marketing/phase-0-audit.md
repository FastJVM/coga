---
slug: marketing/phase-0-audit
title: Phase 0 audit
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - marketing/plan
skills: []
workflow: draft-for-human
secrets: null
---

## Description

Audit what exists vs what the launch needs, per the phase 0 of
`marketing/plan`: the README top (does it tell the post's story?), the blog
and newsletter state, megalaunch and the blocker queue as narrative material
(real examples to quote in post 1 — non-Coga repos like multiply first),
community surfaces, and anything else the essay series depends on (the full
check list is in `## Context`). Two checks are called out because they are
easy to skip: **run the README quickstart end-to-end on a fresh
repo** (a broken first run burns every converted reader), and **assign the
token-measurement collection** post 3 needs during phases 1-2. Output: the
concrete phase-0 worklist, written to this ticket's blackboard.

## Context

**What this is.** An inventory of what exists versus what post 1 needs — not
a review of the plan or the pitch. `marketing/plan` is settled (fork A
pinned); this ticket checks its phase-0 preconditions against reality and
produces a worklist: what must be true before post 1 ships, who owns each
item. Fixing things is out of scope — that's `marketing/readme-top`,
`marketing/discord`, etc. Record findings, not repairs.

**Workflow shape.** `draft-for-human`: the agent runs every check it can
observe and drafts the worklist (step 1); the owner fills in what only they
can see and makes the two assignments (step 2); the agent records the final
worklist (step 3). The worklist lives on this ticket's blackboard, under a
`## Worklist` heading, one line per item: `[owner] item — status/evidence`.

### Checks the agent runs (step 1)

1. **README top** — read `README.md`. Does the first screen tell the post-1
   story (what it is, for whom, the day-shape: "an hour or two in the
   morning, then I leave")? Note the specific gaps for `marketing/readme-top`.
2. **Quickstart, end-to-end** — follow the README install/first-run path
   as a reader would, with one substitution: install *this checkout*
   (`pip install /home/n/Code/coga`) into a fresh venv instead of
   `pip install coga`, because PyPI still has `0.2.0` and this repo is
   `0.3.1`. The owner decided (2026-09-02) that 0.3.1 ships to PyPI before
   post 1; put **"publish 0.3.1 to PyPI"** on the worklist as an owner item
   and do not test the stale package. Then a scratch git repo under the
   scratchpad, `coga init --user`, and `docs/getting-started.md` (where the
   README sends readers) as part of the path under test. Run `coga build`
   only as far as the first composed prompt / first launch attempt — do not
   let a nested agent run to completion. Record every step where the text
   and reality diverge.
3. **Narrative material** — quotable, real examples for post 1, non-Coga
   repos first. Every Coga-run repo on this machine has a `coga/log.md`,
   `coga/tasks/`, and blocker history: `~/Code/multiply` (primary),
   `~/Code/admin`, `~/Code/magicator`, `~/Code/patents`, `~/Code/tablet`,
   `~/Code/xpllm`, `~/Code/coga-hosting-probes`, `~/Code/demo-hackathon`.
   Look for: actual questions agents queued via `coga block`, a real morning's
   answer-review-launch sequence, a megalaunch sweep. Collect 5–10 candidates
   with date + repo + the literal text. Put them on this ticket's blackboard
   under `## Narrative candidates`; `marketing/post-async-megalaunch` reads
   them from there. Read-only — do not modify those repos. `~/Code/admin`
   and `~/Code/patents` are likely confidential: flag any candidate whose
   literal text is not publishable rather than dropping it silently. If the
   non-Coga repos don't yield 5, say so — don't pad from this repo.
4. **Megalaunch state** — is it stable enough to be *described* in present
   tense without lying? Check recent tickets/log entries in this repo for
   megalaunch and watchdog failures. This is a narrative-honesty check, not
   a product review. (From `marketing/positioning`, not attached: comms
   must not promise the felt experience that Slack drops and
   megalaunch/watchdog polish are currently blocking.)
5. **Distribution surfaces** (public, agent fetches and reports):
   - Blog: https://deviantabstraction.com — last post date, newsletter
     signup present?, per-channel URL / analytics feasibility, any existing
     mention of Coga.
   - fastjvm.com — the owner's other venture (YC). Report what the site is
     and whether it has a place a Coga link would fit; audience overlap is
     an owner-only judgment (step 2).
   - HN: user `top256` (karma 213 at ticket authoring, account since 2016;
     `https://hacker-news.firebaseio.com/v0/user/top256.json`). Note recent
     submission pattern and whether the story-submission plan fits the
     account's history.
   - Reddit: `https://www.reddit.com/user/Let047/` — karma, which subreddits
     the owner is already active in (the plan only posts where already a
     member). Reddit often blocks unauthenticated fetches; if so, report
     that and leave it to step 2.
   - Lobste.rs — the owner has an account; username to be supplied by the
     owner in step 2. Check invite/tag fit for a story submission.
   - Community home — does a GitHub Discussions tab or Discord exist yet?
     (`marketing/discord` decides; this ticket just reports the state.)
6. **Token-measurement plan, drafted** — post 3 needs same-task-with-vs-
   without-contexts receipts collected during phases 1–2 (`--prompt-report`,
   schema-2 usage records; see `scripts/human_minutes.py` for the token
   ledger reader). Draft *how* it would be collected and by what mechanism
   (a recurring ticket? a script? manual?), so the owner only has to assign
   it.
7. **Prepared replies** — `marketing/plan` says to write them before post 1
   ships. Do they exist anywhere yet? Report.

### Owner-only items (step 2)

- **Bookface** — login-gated; owner reports standing and whether a pre-HN
  Bookface post is realistic on the planned timeline.
- **Lobste.rs username**, and Reddit/HN nuance the profile doesn't show.
- **fastjvm.com audience overlap** and whether to cross-link.
- **Publish `coga 0.3.1` to PyPI** before post 1 (decided 2026-09-02).
- **Assign** the token-measurement collection (who/what, from the drafted
  plan).
- **Phase-1 thresholds** — the private success numbers the retro will be
  scored against (plan: "noted before publishing, privately is fine").

### Out of scope

- Any fix or rewrite (README, docs, quickstart bugs — file findings, and
  create follow-up tickets only if the owner asks in step 2).
- Re-opening fork A / the essay-series decision.
- Anything from the shelved proof-post apparatus.

**Scope decision (authoring, 2026-09-02).** The evaluator flagged checks 2
and 3 as each big enough to be their own ticket. Kept here deliberately —
the plan assigns the quickstart run to this ticket — but bounded: the
quickstart stops at the first launch attempt, and narrative mining is capped
at 5–10 candidates with an honest shortfall report. If either blows past
that, stop and note it on the worklist instead of finishing it here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
