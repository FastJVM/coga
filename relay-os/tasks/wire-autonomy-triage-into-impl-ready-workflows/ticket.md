---
title: Wire autonomy triage into impl-ready workflows
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
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
step: 1 (design)
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
