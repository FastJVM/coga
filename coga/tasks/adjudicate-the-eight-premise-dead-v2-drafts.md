---
slug: adjudicate-the-eight-premise-dead-v2-drafts
title: Adjudicate the eight premise-dead v2 drafts
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

Dream 2026-08-24 named eight `v2/` drafts as premise-dead. An independent spot-check of four found
the list does **not** hold uniformly: two are confirmed dead, one is demonstrably still alive, and
three carry no recorded evidence at all. Adjudicate each of the eight against the v2 README's
two-question premise test and cancel only those that fail it.

Cancelling a parked draft is a lifecycle write (`coga/log.md` plus a Slack notification) and is
human-only, which is why this ticket runs `code/design-then-implement`: the `design` step produces
an evidence-graded verdict table, the owner approves it at `review-design`, and only then does
`implement` execute the confirmed cancels.

Expected to clear 2 of the 4 `coga validate` errors — but only if the evidence lands that way.

## Context

### Shared background (all three v2 triage tickets)

This ticket is one of three split out of `triage-the-v2-parking-area-empty-descriptions-prem`
(canceled 2026-09-02). Siblings: `correct-the-v2-known-stale-surfaces-table-and-rout`,
`adjudicate-the-eight-premise-dead-v2-drafts`, `interview-the-owner-on-the-17-title-only-v2-stubs`.

Origin: Dream 2026-08-24, Phase 2 knowledge scan (shards 06, 09, 11, 12), classified `gap`.
Re-verified against `main` 2026-09-02 plus an independent cold review. **Where these notes and the
original Dream findings disagree, these notes win.**

**The contract for this directory is `coga/tasks/v2/README.md`.** Read it first — it defines the
two-question premise check (does the subject still exist? do the surfaces it names still resolve?)
and records the `decide-the-fate-of-two-premise-dead-v2-drafts-whos` cancellation precedent.

**Counting `v2/` correctly.** `coga status v2 --all` reports **81 tasks**. Do not count with
`ls coga/tasks/v2/*.md` — that returns 76, counting the `cleanup-core-commands/` directory as one
entry and missing its six children. The Dream scan's "~75" and "18" are both this artifact.

**`coga validate` state.** 4 ERRORs repo-wide, all `unsynthesized-draft-blackboard`, all under
`v2/`. The rule fires only on `status == "draft"` (`src/coga/validate.py:447`), so each clears by
cancelling or synthesizing. Everything else `coga validate` prints is a WARN. Two errors clear in
`correct-the-v2-known-stale-surfaces-table-and-rout`, two in
`adjudicate-the-eight-premise-dead-v2-drafts`. **A green validate is never a reason to cancel a
draft** — it is a consequence of correct verdicts, never an input to them.

### The cohort, graded by evidence — do not treat it as a flat list

**Confirmed dead (evidence verified — cancel is correct):**
- `audit-rules-md-usage-across-relay-and-decide-wheth` — `rules.md` survives only as a stale-artifact
  fixture in a prune test (`tests/test_init.py:1379`); the "Global rules" compose layer it audits is
  gone (`grep rules src/coga/compose.py src/coga/paths.py` is empty).
- `document-workflow-less-concept-capture-drafts-as-s` — deliverable shipped at
  `coga/contexts/coga/architecture/SKILL.md:363-400`, which names the exact validator-nagging
  problem the draft was written about.

**Subject was never built, not deleted — this is NOT the README's premise test:**
- `autotrigger-ticket-type` — the evidence offered was "every cross-reference dead" (6 of 7 named
  slugs confirmed absent). But dead cross-references make a draft harder to *act on*; they do not
  make its subject gone. Recurring is alive (`src/coga/recurring_runner.py`, three workflows under
  `coga/workflows/`), so the proposed recurring+idle trigger unification was never built.
  Re-adjudicate on the README's actual two questions.

**Cancel only if the surviving residue is named in the reason:**
- `skill-update-aborts-on-uncommitted-log-file` — the stated root cause is genuinely gone
  (`src/coga/commands/launch_script.py` and `run_script_mode` no longer exist). But its secondary
  finding is live: `_assert_no_unmerged_paths` (`src/coga/skill_manager.py:417`) still filters on
  `--diff-filter=U` only, so an ordinary dirty tracked file still walks past it into `_checkout`
  (line 488). A bare cancel silently drops a real bug — either name the residue in the cancel reason
  or open a follow-up for it.

**Asserted with no recorded evidence — re-derive before touching:**
- `dev-loop-git-hygiene`, `relay-design-repositories`, and
  `split-context-to-doc-user-accessible-and-editable` were each given a one-clause reason ("settled
  the other way", "question answered by shipped precedent") with no pointer to where that settlement
  is recorded. Find the evidence or downgrade the verdict.
- `add-relay-skill-search-with-candidate-eval` was listed as settled and **is not**. `coga skill`
  exposes install / install-local / install-url / update / remove / status — there is no `search`.
  The subject was never built, the surfaces it names are still live, and `coga/log.md` records no
  decision, cancel, or counter-ticket. It passes both of the README's questions. **Do not cancel
  this one** absent new evidence.

### Deliverable of the `design` step

A verdict table: one row per slug with the verdict (cancel / keep / keep-with-follow-up), the
specific evidence (file:line or command output), and the exact cancel reason text where applicable.
The owner approves this table at `review-design`. Do not run any `coga mark canceled` before that
gate. Spelling: `coga mark canceled v2/<slug> --message "<reason>"`.

### The incentive to watch

Two of the four `coga validate` errors sit on `autotrigger-ticket-type` and `split-context-to-doc`,
so ruling them dead is the cheapest route to a green gate. **A green validate is never a reason to
cancel.** Adjudicate on the README's two questions alone and accept a still-red validate if that is
where the evidence lands — the sibling ticket clears the other two errors regardless.

Do not synthesize the blackboard of any draft you cancel; synthesis for the two drafts that keep
that route belongs to `correct-the-v2-known-stale-surfaces-table-and-rout`.

### Out of scope

The 17 title-only stubs (sibling ticket) and the README stale-surfaces table (sibling ticket).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
