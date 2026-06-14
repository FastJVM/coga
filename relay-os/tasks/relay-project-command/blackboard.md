The blackboard is a notepad to be written to often as the human and agent works through a task.

## 2026-06-12 — Step 1 (design): interview design + rationale

The settled four-question interview lives in `ticket.md` under
"Interview design". This section records *why* it has that shape — the
evaluation that produced it (independent agent review of an earlier draft
Zach worked up) — and the open questions implementation must still
settle.

### Why this shape (three decisions that moved the design)

1. **Outcome (Q1) before the doc-seed (Q2), always.** An earlier draft
   opened with the doc question ("read the doc, classify, ask only about
   gaps"). That has a cold-start bug: you can't know what a *gap* is
   until you know the target outcome, and vision docs are routinely vague
   on the concrete "what exists when done." If the agent gap-fills off
   the doc alone it silently skips outcome-probing and decomposes against
   a fuzzy finish line. Fix: Q1 is mandatory regardless of the doc; the
   doc only lets the agent skip *constraint/dependency* gaps (Q3/Q4),
   which docs do usually specify.

2. **The cut "out of scope" question is safe only because the review
   step is built.** This interview is harder than `init/setup`'s: its
   output is an *ordered dependency graph of tickets*, not independent
   artifacts, so vagueness doesn't degrade gracefully — it produces wrong
   tickets and wrong edges. The single most likely decomposition failure
   is **granularity** (agent slices into 3 mega-tickets or 15 trivial
   ones), which no question constrains well — it's fixed by the human
   *reacting* to a proposed list, not predicting up front. The
   review-before-scaffold step is therefore load-bearing: it covers the
   cut scope question (over- and under-scoping), the granularity failure,
   and per-ticket acceptance criteria in one move. If implementation
   can't deliver that step, reinstate a scope question.

3. **Q3/Q4 reseamed along real seams.** An earlier Q2 bolted "what's
   fixed" (constraints) onto "who signs off" (assignee routing) — two
   unrelated frames; people answer one and stall on the other. Sign-off
   moved into the dependency beat (Q4), because "who has to approve"
   is itself a sequencing dependency. Q4 bundles external blockers +
   hidden order + sign-off, which all read as "what must happen before
   what" — one coherent frame, so the bundle holds.

### Acceptance criteria — captured once, drafted per-ticket

Q1's "how would you demo it" yields the *project-level* done bar (the
final ticket's review bar). Intermediate tickets (1…N-1) get
agent-drafted acceptance criteria that the human corrects in the review
step — deliberately not an interview question. (Once the
`acceptance-criteria` ticket lands a real AC field, generated tickets
should populate it.)

### Open implementation questions (for the design write-up / next step)

- **Is "review before scaffold" a workflow step or interview protocol?**
  Leaning: a real step in this command's flow, modeled on `init/setup`'s
  `scan-and-generate` → `review-and-sign-off`. Needs deciding before
  implement.
- **Dependency representation in the generated tickets.** Q4 produces a
  dependency graph; how is it recorded on each draft? This is exactly the
  `identify-blocking-issues` ticket's proposed `dependencies:` field —
  coordinate so `relay project` emits whatever format that ticket settles
  on, rather than inventing a parallel one.
- **Doc-seed input mechanism — narrowed 2026-06-13 (see below).** Folds
  onto `relay setup`'s seed arg (e.g. `relay setup "<idea, or path/link to
  a vision doc>"`), matching the seed `relay project` already accepts.
  Exact fetch-vs-path handling still open.
- **Bulk draft creation.** `relay draft`/`relay ticket` scaffold one
  top-level ticket at a time; project planning needs to emit an ordered
  set. Does it call the existing scaffold path in a loop, or is there a
  new batch path? Ordering must survive (slugs are leaf-name based). (The
  built `bootstrap/project` skill already loops `relay draft` per ticket
  during the session — see the decision note below.)
- **Command vs. ticket-driven — RESOLVED 2026-06-13 (see below).** Neither
  a standalone `relay project` command nor its own bootstrap ticket: it
  ships as `relay setup`'s already-onboarded path. The existing
  `bootstrap/project` skill (the interview + scaffold protocol) is reused
  as-is; only the entry point changes.

## 2026-06-12 — Design dry-run (wizard-of-oz validation)

Ran the four-question interview by hand against a real project ("killer
demo video for Relay's launch") before writing code, the same way
`init/setup` was validated before it was wired in. The interview produced
an ordered 7-ticket set; the human pruned it to 5 in one reaction. The
design held. Three findings:

1. **Q4 (dependencies) was the highest-value answer — keep it.** The
   human's "I need to build a proper Gmail flow first" surfaced the entire
   prerequisite chain (test account → build the flow → *then* record it).
   The outcome alone (Q1) would have led to "record a comparison video"
   and missed that the demo's *subject* must be built before it can be
   filmed. Ordering correctness came from Q4, not Q1.

2. **The cut-scope tradeoff is validated.** With no standalone "what's out
   of scope?" question, the review-before-scaffold step still bounded
   scope correctly: it caught two over-generated tickets (a redundant
   "polish the workflow" and a standalone "boss approval" that was really
   a review step) plus one granularity question, all fixed by the human
   *reacting* to the concrete list. Evidence that the short interview +
   review gate beats a longer interview.

3. **Q2 wording fix applied.** As originally worded ("Is there a *doc*?")
   Q2 got "no" — then the human immediately named an existing **workflow
   file** (`browser/build-automation`) that shaped the whole "with
   workflow" arm of the demo. The narrow "doc" wording nearly lost
   load-bearing prior art. Broadened in `ticket.md` to "a doc … or
   existing work like a workflow, script, or code." Implementation should
   carry the broadened wording into whatever runs the interview.

## 2026-06-13 — Decision: fold project planning into `relay setup`, drop the standalone command

Zach's call after reviewing the commands already built on branch
`relay-cli-commands`: do not release `relay project` as its own command;
make project planning the already-onboarded path of `relay setup`. Setup
and project are the same operation — interview about intent → draft
tickets — at two altitudes (repo on first run, project after), so one
command is fewer to learn, and there's nothing to deprecate since `relay
project` isn't shipped. This also resolves the "command vs. ticket-driven"
open question above: it's neither — it's a branch of `relay setup`.

**What this changes in the code already on this branch:**

- `relay setup` (`src/relay/commands/setup.py`) currently ends its
  resumable flow this way: if the `relay-setup` ticket is `done`, print
  "already set up — nothing to do." That terminal branch becomes the
  project-planning entry — confirm, then run the project flow.
- The project flow is already built: `relay project`
  (`src/relay/commands/project.py`) is a thin launcher over the
  `bootstrap/project` skill, which holds the four-beat interview and the
  review-before-scaffold protocol (and loops `relay draft` per ticket).
  Reuse it wholesale — `setup` calls the same path. Implementation is
  "rewire + delete a registration," not build-from-scratch.
- Remove the `app.command("project")(...)` registration in
  `src/relay/cli.py` and drop `"project"` from the alias/command list
  there (~line 102). The skill and launcher logic stay; only the
  user-facing command word goes away.

**Two refinements settled with the decision:**

1. **Pre-load round-one intent.** Feed the repo-level intent `relay setup`
   captured (the `relay-setup` ticket's recorded answers, plus the
   generated contexts/rules) into the project interview as context. The
   agent decomposes against known repo background and never re-asks "what
   is this repo for"; the four project beats stay, project-level only.
2. **Confirm before planning.** A bare `relay setup` on an onboarded repo
   no longer silently no-ops — it asks "This repo's set up — plan a new
   project? [y/N]" before starting an interactive session, so the same
   command run twice doesn't surprise a returning user. A seed arg is
   read as explicit intent and skips the confirm, dropping straight into
   planning.

**Supersedes:** the relay-cli `feat/init-interview` branch
(interview-at-`init`). That approach is replaced by
interview-in-a-launched-ticket, which PR #348 already shipped — nothing
to merge from it.
