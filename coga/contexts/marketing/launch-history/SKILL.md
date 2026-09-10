---
name: marketing/launch-history
description: Archived Coga launch programs and proof-post apparatus. Historical reference only; do not attach to live launch tickets.
---

# Archived Coga launch programs

This context preserves launch apparatus that is no longer part of the live
plan. The current plan is `marketing/plan`. Nothing here is a ship instruction
or an active phase, and this context stays unattached so it does not compose
into launch work.

## Fresh-start archive — 2026-09-10

The owner requested a grouped catalogue followed by fresh marketing planning,
using the previous work as inspiration. These snapshots preserve the material
before that reset; their instructions and commitments are historical:

- [Three-essay plan](three-essay-plan.md): ideas, beats, sequence, replies,
  readiness gates and the earlier execution list.
- [Distribution plan](three-essay-distribution.md): dated account evidence,
  channel order, YC timing, title tactics, scorecard and miss branches.
- [Positioning](positioning-before-reset.md): prior message, audience, voice,
  strategic fork and competitive framing.
- [Campaign ticket briefs](campaign-ticket-briefs.md): earlier launch-plan,
  essay, README and community briefs, including detailed HN/blog research.

Use the [current catalogue](../map/SKILL.md) to find material by subject and
the [current plan](../plan/SKILL.md) for the new preparation order. The older
program history below also describes prior choices, not current gates.

## Superseded "20 minutes a day" program

On 2026-08-18/19, the owner replaced a launch led by a pre-registered two-week
experiment with a series of idea essays. The experiment held its hook hostage
to an unknown result, gated the story on megalaunch stability, and buried the
message under measurement apparatus.

The old tickets, `v2/launch-20-minutes-a-day` and `v2/add-killer-demo`, were
deleted on 2026-08-19. Their source text remains in git history at commits
`9a93bff0` and `bedd29e2`.

## Shelved proof-post option

The proof post was a two-week pre-registered experiment framed around a
recomputable ledger of every attempt. It survives as an option, not phase 4 of
the current launch. It has no active ticket. The former plan deferred
reconsideration until after the three-post essay series and sustained
megalaunch use. That sequence is now historical; any future measurement
proposal needs its own owner decision and brief. The marketing token
experiment remains dropped.

The tracked apparatus that remains available is:

- `scripts/human_minutes.py`, covered by
  `tests/test_human_minutes_script.py`: human-attention episodes computed from
  public timestamps with its measurement parameters pinned in code (10-minute
  gap, 2-minute floor, 5-minute sensitivity floor);
- the same script's machine-token ledger, read from schema-2 usage records;
  and
- `docs/velocity-report.md`, section "Why there is no multiplier here": the
  pre-registration and intention-to-treat rule that every completed, blocked,
  rescued, or abandoned attempt must be counted and linked to its receipt.

The fallback what-broke field-report framing and the old demo brief exist only
in the deleted tickets' git history. A future proof-post ticket must re-decide
them rather than treating them as approved. The former campaign excluded
this apparatus from its three essays.

## Paired token/time experiment — retired 2026-09-09

The owner dropped this requirement from the marketing launch. It had been
intended to test the documentation-as-cache premise. The former post-3 brief
replaced it with a public context and evidence of its use in a later session.
The fresh-start plan has not selected that essay. Do not create a collection
ticket or require
paired runs from this archived protocol. Operational usage tooling is separate.

The protocol below is preserved solely as historical rationale:

### Former protocol

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
