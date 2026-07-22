---
slug: implement-accepted-ticket-interview-improvements
title: Implement accepted ticket-interview improvements
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Implement the six accepted changes (all P0 + P1 items; P2 deferred) from the
interview-improvement proposal on `improve-prompt-for-relay-ticket`'s
blackboard. All are edits to the `bootstrap/ticket` skill text plus tests — no
CLI behavior changes:

1. **Ask for "done" up front** — the new-title greeting and the Step 3
   Description prompt become "what should it do, why now, and what would count
   as done?"; done criteria land as a sentence in `## Description`, not a new
   section.
2. **Checklist-shaped context question** — replace the Step 3 "what will the
   agent wish they knew?" prompt with concrete buckets: files/modules/commands
   to inspect, related tickets or PRs, constraints and out-of-scope lines,
   known traps, verification commands, safety/rollback. One targeted follow-up
   on a thin answer (code vs docs variants are drafted in the proposal).
3. **Evaluator severity rubric** — Step 6 evaluator assesses the axes
   Objective, Done, Scope, Knowledge, Workflow fit, Safety, and marks each
   finding `must-fix before launch` / `nice-to-have` / `question for human`.
   The authoring agent must resolve must-fix items (edit the body directly, or
   ask the human one concrete question and then edit) before the session ends.
4. **Thin-answer recovery rule** — never write a blank/title-only
   `## Description`, or a blank `## Context` on a non-concept-capture ticket,
   without one follow-up; deliberate concept-capture stays a workflow-less
   draft with one sentence in the body saying so.
5. **Fix stale task-shape guidance** — example/path wording must cover both
   real layouts: flat `coga/tasks/<slug>.md` and nested
   `coga/tasks/<group>/<slug>/ticket.md`, excluding support files.
6. **Conservative Step 4** — create a context/skill inline only when the future
   launched agent needs that exact body and the human confirms the name;
   speculative gaps go to a `## Proposals` blackboard note instead.

Done means: the packaged skill text carries all six changes while keeping the
4–6-question interview budget; `tests/test_bootstrap_ticket_skill_template.py`
asserts the shipped template mentions done-criteria, the concrete context
buckets, both current task shapes, and the evaluator severity/synthesis rules;
`python -m pytest` passes.

## Context

- Target file: `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
  Despite the proposal saying "both live and packaged copies", this repo has
  **no** live override under `coga/skills/` for the bootstrap namespace — the
  packaged copy is the single source. The copy under
  `.venv/.../site-packages/coga/...` is install output; don't edit it, and
  check whether the active install serves `src/` directly or needs a reinstall
  to pick up template changes.
- `eval/ticket-diagnostic` was **removed** in PR #603 ("fold its one real
  signal into ticket Step 6"). Do not resurrect it; change 3's axes come from
  its old rubric and now live only as Step 6 wording.
- Step 7 already contains a post-confirmation cleanup pass that folds durable
  blackboard substance into the body. Change 3's delta is the Step 6 rubric,
  severity marking, and the must-fix-before-close gate — not the fold-back
  itself.
- Exact suggested prompt wording for each change is in the "Ranked changes"
  section of `improve-prompt-for-relay-ticket`'s blackboard — read it first;
  the quoted texts are ready to adapt.
- Keep it lean: the skill deliberately targets a 4–6 question interview
  (`docs/vision.md`, Coga principles). Fold "done" into existing questions
  rather than adding new ones.
- Out of scope: a formal `Acceptance Criteria` body section (P2 — deliberately
  deferred); changes to `coga ticket` command behavior unless the text change
  exposes a real CLI mismatch.
- The repo is mid Relay→Coga rename; use Coga wording in any text you touch.
- Verify with `python -m pytest` and eyeball `coga ticket` composing the
  updated skill if practical.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
