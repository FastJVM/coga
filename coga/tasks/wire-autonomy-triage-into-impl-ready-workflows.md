---
slug: wire-autonomy-triage-into-impl-ready-workflows
title: Wire autonomy triage into impl-ready workflows
status: done
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- autonomy/triage
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Wire the general `autonomy/triage` test into ticket **authoring time** so every
new ticket is classified into an autonomy tier as part of being created, and
that classification informs how the ticket is set up before work begins.

This follows `automation-triage`, which shipped the reusable rubric context and
the four tier workflows:

- `autonomy/fully-automated`
- `autonomy/assist-only`
- `autonomy/human-verify`
- `autonomy/human-only`

**Direction note (premise reversed from the original draft).** The predecessor
ticket and the first draft of this one targeted *impl-ready* — a thin triage step
inside the `code/*` path, run after design. The owner reversed that here: triage
belongs at **authoring (`relay ticket` / `bootstrap/ticket`)**, not impl-ready.
The reason is structural. The output of `autonomy/triage` is a *tier*, and each
tier **is** one of the four `autonomy/` workflows (the rubric: "each tier is
realized by the `assignee:` choices in its matching `autonomy/` workflow"). A
triage step seeded *inside* an already-frozen `code/*` workflow runs after the
workflow is chosen and cannot re-route the task — it can only tune assignees on
the remaining steps. To actually let triage select among the tier workflows, the
test has to run **before the workflow is frozen**, which is exactly the
`bootstrap/ticket` interview (workflow selection is its step 3). So the wiring
point is the authoring skill, not the implementation workflows.

The tradeoff accepted: at authoring the change is less fully understood than at
impl-ready, so Q3 (failure radius / verifiability) is judged on the interview's
description + context rather than a completed design. The `bootstrap/ticket`
interview plus its evaluator review is treated as enough signal to classify; a
mis-classification is correctable by the owner at review time, the same as any
other authoring choice.

## Acceptance Criteria

- The `bootstrap/ticket` skill gains an explicit autonomy-triage step that runs
  the `autonomy/triage` 3-question test during authoring and classifies the
  ticket into one of the four tiers.
- The skill instructs the interviewer to use the rubric: the skill body either
  points to `relay-os/contexts/autonomy/triage/SKILL.md` or has it attached, so
  the test is applied from the canonical rubric rather than re-derived.
- The resulting tier (plus a one-line rationale per question) is shown in the
  skill's step-7 summary so the human sees and validates the classification
  before launch. No new ticket field or body section is introduced — the tier is
  expressed through the chosen workflow/assignees.
- The triage result **informs** the workflow choice (skill step 3) — the skill
  documents an advisory tier→workflow mapping — without silently overriding a
  workflow the human explicitly picks, and without encoding `mode` semantics.
- The live skill and its packaged mirror under
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`
  stay byte-for-byte in sync (CLAUDE.md seed-sync rule).
- The change does **not** add a triage step to `code/*`, `dev/*`, or the
  `_template` workflow, does not edit the task `_template` ticket, and does not
  touch `browser/build-automation`'s separate browser-specific failure-radius
  triage.
- `relay validate --json` passes (modulo the pre-existing unrelated backlog
  failures recorded by `automation-triage`).
- Any test that asserts on `bootstrap/ticket` skill content or authoring prompt
  composition is updated; if the change is skill-text only with no code path
  touched, note that no test change is required.

## Proposed Shape

The whole change is in the authoring skill; no workflow files change and no new
ticket field/section is introduced.

**Files**

- `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` — primary edit.
- `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`
  — packaged mirror, kept byte-for-byte identical.

**Skill edit (the substance)**

1. Add a triage step to `bootstrap/ticket`, placed in the interview flow
   *before* the workflow is finalized — woven into or immediately ahead of the
   current **step 3 (Workflow)**. After Description/Context are gathered (steps
   1–2), run the `autonomy/triage` 3-question test against the task.
2. The step reads the rubric from `relay-os/contexts/autonomy/triage/SKILL.md`
   (the context is also attached to this ticket so the implementer has it in
   front of them). It applies the three questions, lands on a tier
   (`fully-automated` / `assist-only` / `human-verify` / `human-only`), and
   captures a one-line answer per question.
3. The tier **informs** the step-3 workflow recommendation — advisory, never
   overriding a workflow the human explicitly picks. Document an advisory mapping
   in the skill (authored here, grounded in the rubric + the four `autonomy/`
   workflows): `human-only` → `autonomy/human-only`; `assist-only` →
   `autonomy/assist-only`; `human-verify` → a workflow with an owner gate before
   the irreversible step (the existing `code/*` workflows already qualify);
   `fully-automated` → an all-agent workflow, and may *suggest* an unattended
   `mode` (`script`, or `auto` = script + `claude -p`). Do **not** encode `mode`
   semantics or a tier↔mode mapping here — that is a separate ticket (see Out of
   Scope / blackboard).
4. The tier is **expressed through** the chosen workflow + assignees (+ `mode`),
   per the rubric ("each tier is realized by the `assignee:` choices in its
   matching `autonomy/` workflow") — it is **not** stored in a new ticket field
   or body section. Surface the classification + the one-line per-question
   rationale in the **step-7 summary** block so the human validates it alongside
   workflow and contexts before launch. The summary is the only durable
   surface this ticket adds.

**Order of work**

Edit the live skill → mirror to packaged copy → `relay validate --json` → grep
both skill copies match byte-for-byte → update/confirm any `bootstrap/ticket`
content tests.

## Out of Scope

- Rewriting the autonomy rubric or tier workflows shipped by
  `automation-triage`.
- Adding an `assist-only` branch to `browser/build-automation`, or otherwise
  touching its separate browser-specific failure-radius triage.
- Adding a triage step to the `code/*`, `dev/*`, or `_template` **workflows**
  (the impl-ready framing this ticket explicitly reversed).
- Hard, non-overridable tier→workflow auto-selection.
- **Representing the autonomy tier as a structured value in `mode`**
  (`autonomous` / `human` / `human+ai`) and reconciling it with the
  `interactive` / `auto` / `script` taxonomy (`script` = a launch; `auto` =
  script + `claude -p`). This is the tier's eventual home but is split to a
  **separate ticket** (filed: see blackboard).
- Any `relay.toml` extension-field schema change.

## Context

The upstream split was deliberate: `autonomy/triage` and the `autonomy/` tier
workflows are library artifacts until this follow-up attaches them to the
general path. This ticket is the tracked consumer that ends their orphan window.

`autonomy/triage` is a **context** (rubric), not a skill — `bootstrap/ticket` is
the **skill** that will invoke it. The skill body lives at
`relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` (packaged mirror under
`src/relay/resources/templates/...`); `relay ticket` injects it via
`AUTHORING_SKILL` in `src/relay/commands/ticket.py`. The shim ticket attaches no
contexts of its own, so the rubric reaches the interviewer through the skill body
reading the context file (or via this ticket's attached `autonomy/triage`).

This wiring is authoring-time and general; it is independent of
`browser/build-automation`, whose 3-outcome failure-radius triage is a separate,
narrower concern and is left untouched.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design decisions (this session)

- **Premise reversed: authoring-time, not impl-ready.** Owner (nick) decided
  triage runs at `relay ticket` / `bootstrap/ticket`, reversing both the
  predecessor (`automation-triage`) and the original draft of this ticket.
  Rationale: tier == workflow, so triage must run *before* the workflow is
  frozen; a step inside a `code/*` workflow runs too late to re-route. Full
  reasoning is in the ticket Description.
- **Surface area shrank.** No `code/*` / `dev/*` / `_template` *workflow* step
  is added. The change is concentrated in the `bootstrap/ticket` skill (+ its
  packaged mirror) plus an `## Autonomy` section on the task `_template`.

## Open Questions — RESOLVED by owner (this session)

1. **Advisory vs. mandatory tier→workflow mapping.** → **Advisory.** Tier informs
   the step-3 recommendation; human can override. (A `human-verify` code task can
   still use `code/with-review`.)
2. **Where to record the tier.** → **In `mode`** (`autonomous` / `human` /
   `human+ai`) — but that representation is **its own ticket** (filed below).
   This ticket adds **no** `## Autonomy` field/section and does **not** edit the
   task `_template`. The tier is expressed via the chosen workflow/assignees and
   shown in the step-7 summary only.
3. **`fully-automated` → mode?** → Triage may **suggest** an unattended mode
   (`script`, or `auto` = script + `claude -p`); do not auto-set, do not encode
   mode semantics here. Note: the predecessor ticket's "`mode: auto` is disabled"
   claim is *not* carried forward — owner's taxonomy differs; mode is the other
   ticket's job.
4. **Evaluator checks the tier?** → No special instruction needed; the owner's
   review already scrutinizes the classification.
5. **Active-edit re-classification?** → **No need** — human edits handle it. No
   special branch.

No open questions remain blocking. The spec is fully specified.

## Follow-up ticket (filed)

Per owner: the structured representation of the tier in `mode` (autonomous /
human / human+ai), reconciled with interactive/auto/script, is split out. Filed
as a draft: `represent-autonomy-tier-in-ticket-mode-field` (needs a
`bootstrap/ticket` interview to scope + pick a workflow before activation).

## Note on ticket status

This ticket is still `status: draft` (predecessor filed it as a draft). The
design step ran against it anyway. The owner will need `relay mark active`
before the implement step can run for real — flagging so it isn't a surprise at
the review-design → implement boundary.

**UPDATE (implement step):** Resolved — ticket is now `status: in_progress`,
`step: 3 (implement)`. Owner activated it; the draft note above is stale.

## Dev

- branch: `wire-autonomy-triage-authoring`
- worktree: `../relay-autonomy-triage-authoring`
- pr: https://github.com/FastJVM/relay/pull/328

## Implement step notes

**Scope correction vs. stale design bullet.** The "Design decisions" bullet at
the top says the change includes "an `## Autonomy` section on the task
`_template`". That is contradicted by the resolved Open Questions (#2) and the
final ticket Acceptance Criteria, which are authoritative: **no new field/section,
no edit to the task `_template`.** Implementing to the ticket AC, not the stale
bullet. The tier is expressed only via chosen workflow/assignees + the step-7
summary.

**Change is skill-text only.** Edit `bootstrap/ticket` SKILL.md (live + packaged
mirror, kept byte-identical). No code path touched. Tests in `tests/test_ticket.py`
use a synthetic fixture skill body (not the real shipped text) and assert only on
the injection mechanism (`Skill: bootstrap/ticket` in the composed prompt), so
**no test change is required** (per the ticket's own AC clause).

**Edits made:**
- Step 3 interview: inserted a new item 3 **Autonomy triage** (after Context,
  before Workflow) that runs the 3-question test from
  `relay-os/contexts/autonomy/triage/SKILL.md`, lands on a tier, captures a
  one-line rationale per question, and documents the advisory tier→workflow
  mapping. Renumbered Workflow→4, Contexts→5, Assignee→6, Extension→7.
- Step 3 Workflow item: triage tier advises the recommendation, never overrides
  an explicit human pick.
- Step 7 summary: added an `Autonomy tier` block (tier + per-question rationale)
  and noted it in the step intro.

**Seed-sync reality (worth knowing for review/open-pr).** Both skill paths sit
under upstream-managed `bootstrap/` trees, but their git status differs:
- Packaged mirror `src/relay/resources/templates/relay-os/bootstrap/.../SKILL.md`
  is **tracked** → this is the committed source of truth.
- Live `relay-os/bootstrap/.../SKILL.md` is **gitignored** (seed-managed,
  regenerated by `relay init --update`) → not committed, but I synced it
  byte-identical in the working checkout so the running repo behaves now.
`git add` of the packaged file prints an advisory "ignored" hint (the parent
dir matches an ignore pattern) but still stages the tracked file — commit went
through fine.

**Verification (implement step):**
- `python3.12 -m pytest` → **623 passed, 1 skipped** (pre-existing skip).
  Note: repo `python` is 3.9 (no `tomllib`); use `python3.12` to run the suite.
- `tests/test_ticket.py` → 7 passed.
- `relay validate --json` → 2 errors, both **pre-existing & unrelated**
  (`relay-additions-spec`, `split-context-to-doc-...` missing-step) — excluded
  by the ticket AC. No new validation issues from this change.
- Both skill copies byte-identical; worktree tree clean after commit.

**Commit:** `453a435` on branch `wire-autonomy-triage-authoring`
(worktree `../relay-autonomy-triage-authoring`). No push / no PR — that's the
`code/open-pr` step next.

## Review step — Codex 2026-06-16

- PR #328 is already merged: https://github.com/FastJVM/relay/pull/328
  (`453a435` merged via `44d1080` on 2026-06-10).
- Reviewed the PR diff: one packaged `bootstrap/ticket` skill text change, no
  code/workflow/template-skeleton/browser-triage changes. The diff matches the
  final Acceptance Criteria and the implement-step scope correction.
- Verified `origin/main` contains the autonomy-triage authoring text in the
  packaged skill. No review findings.
- Task-scoped validation: `relay validate --task
  wire-autonomy-triage-into-impl-ready-workflows --json` -> `ok_count: 1`, no
  issues.

## Closure note — 2026-06-30

Owner asked whether this is obsolete now that Coga has megalaunch. Confirmed the
ticket itself is stale rather than superseded by megalaunch: the requested
Relay-side authoring-time autonomy triage change already shipped in PR #328 and
was logged done on 2026-06-15. This Coga task copy was accidentally relaunched
to `in_progress`; close it instead of re-running the design workflow.
