---
slug: the-ticket-interview-never-asks-what-done-means
title: The ticket interview never asks what done means
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

`bootstrap/ticket` never asks the filer what would count as done. The new-title
greeting is "What should it do, and why? I'll turn your answer into the ticket",
and the Step 3 question list runs Description → Context → Workflow → Contexts →
Assignee → extension fields. Nothing anywhere asks for a definition of done, so
tickets reach `implement` with intent but no agreed finish line.

Three separate efforts have asked for this independently and every one of them
parked before it landed, so the gap is still open in the shipped skill. This
ticket is the single owner of the question and supersedes both parked drafts
(see below). It has to settle two things and then implement the outcome:

1. **Does the interview ask, and how?** Wording, and where it fits inside the
   deliberate 4–6 question budget.
2. **Where does the answer land?** Prose inside `## Description`, or a
   first-class `## Acceptance Criteria` section that `coga validate` checks.

Question 1 was already answered once (yes, as prose). Question 2 is the part
that was deferred and never resolved. Do not treat question 1 as reopened
without a reason drawn from the prior art below.

## Context

### Prior decisions — this ticket is a rediscovery, not a new idea

- **`improve-prompt-for-relay-ticket`** (done 2026-07-22) ran this analysis and
  produced a ranked proposal on its blackboard. Verdict: *ask for "done" up
  front, and land it as a sentence in `## Description`, not a new section.* A
  formal `## Acceptance Criteria` section was ranked **P2 and deliberately
  deferred**. **The file was deleted in `ffb0a383` (2026-07-23) — it is not on
  disk.** Recover it before you start; it is the most load-bearing prior art
  here and it already contains ready-to-adapt prompt wording:

  ```
  git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md
  ```

  In that blob: `### Ranked changes` at line 185, the P0 greeting wording at
  ~196 (*"What should it do, why now, and what would count as done?"*), and the
  explicit P2 deferral (*"Do not add a permanent `Acceptance Criteria` section
  yet"*) at ~319.
- **`v2/implement-accepted-ticket-interview-improvements`** (paused 2026-07-27,
  "Parked to v2 for the release") carries that verdict as change 1 of 6. Its
  `## Context` also says a formal Acceptance Criteria section is out of scope
  for it.
- **`v2/acceptance-criteria`** (zach, paused 2026-07-01) wants the opposite
  emphasis: an acceptance-criteria slot on the ticket format, the interview
  question, *and* a `coga create <slug> --ac1 "..." --ac2 "..."` CLI flag.
- **Dream 2026-08-24**, Phase 2 knowledge scan (shard-12), classified this a
  `gap` and filed the present ticket, unaware of all three.

**This ticket supersedes `v2/acceptance-criteria` entirely, and change 1 of
`v2/implement-accepted-ticket-interview-improvements`.** Both have a note
pointing here. The other five changes in that ticket (context buckets,
evaluator severity rubric, thin-answer recovery, stale task-shape guidance,
conservative Step 4) stay with it and are out of scope here.

### Prior art that constrains the answer

- **`## Acceptance Criteria` already exists in this system.** The `code/design`
  skill writes a ticket body of Description / Acceptance Criteria / Proposed
  Shape / Out of Scope, and `code/design-then-implement`'s `review-design` gate
  is the owner reviewing exactly that. Any answer must say how an
  interview-authored section relates to the design step's — same section
  reused, or two authors fighting over one heading.
- **Most tickets never run `code/design`.** `code/with-review`,
  `code/with-self-review` and `direct/body` have no design step, so today a
  ticket only gets acceptance criteria if it happened to pick the one workflow
  that writes them. That asymmetry is the real argument for putting the
  question in the interview instead.
- **`coga validate` has no body-prose checks today** — every check is
  frontmatter, refs, secrets, or workflow/step shape. The one precedent for
  reading the body region is `unsynthesized-draft-blackboard`
  (`src/coga/validate.py`, in `_check_one_task`): draft-only, error severity,
  reads the blackboard region. If an AC check is added, that is the model to
  follow, and adding it means the validator starts inspecting body prose for
  the first time — a real widening, not a one-line addition.

### Where the code is

- **Skill text: one file, one edit.** The single source is
  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
  `coga/.agent-skills/bootstrap/ticket` is a **symlink** into it. An earlier
  version of this ticket called them an "identical pair" to keep in sync —
  that was wrong; there is nothing to sync. Do not edit the copy under
  `.venv/.../site-packages/coga/` (install output); check whether the active
  install serves `src/` directly or needs a reinstall to pick up changes.
- **Ticket template: a genuine twin pair.** `coga/tasks/_template/ticket.md`
  and `src/coga/resources/templates/coga/tasks/_template/ticket.md` are two
  real files, currently byte-identical. If a section is added to the template,
  both must change (CLAUDE.md live/packaged sync rule).
- **Validator:** `src/coga/validate.py`.
- **Tests:** `tests/test_bootstrap_ticket_skill_template.py` already asserts
  properties of the shipped skill text — extend it rather than starting a new
  file. `tests/test_ticket.py` covers `coga ticket`.

### Constraints and traps

- **The 4–6 question interview budget is deliberate** (`docs/vision.md`, Coga
  principles, and the skill's own Step 3). Fold "done" into an existing
  question; do not add a seventh.
- **Microkernel rule** (CLAUDE.md): skill and template text is the edge. Only
  reach into `src/coga/` if the validator check genuinely needs Python logic.
- **Grandfathering is the hard part of the validator option.** As of
  2026-09-01, **17 of 151** ticket files under `coga/tasks/` already have an
  `## Acceptance Criteria` section (`grep -rl '^## Acceptance Criteria'
  coga/tasks --include=*.md | wc -l`) — mostly tickets that ran `code/design`.
  So the section has real de-facto adoption, but ~89% of tickets lack it and an
  error-severity check would fail the repo on day one. Decide severity, which
  statuses it applies to, and whether it is draft-only like its precedent. Also
  check whether those 17 existing sections share a shape the check could
  actually assert — if the design step's freeform criteria and an
  interview-authored version disagree, the check has no stable target.
  `coga validate --json` on this repo is the smoke test — run it before and
  after.
- **Zach's `--ac1/--ac2` CLI flag**: decide explicitly in or out and say why.
  New CLI surface needs a stronger justification than a text change, and
  `coga create` currently writes only the scaffold.
- The repo is mid Relay→Coga rename; use Coga wording in anything you touch.
- Verify with `python -m pytest` and `coga validate --json`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
