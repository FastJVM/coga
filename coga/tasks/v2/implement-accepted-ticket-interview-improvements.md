---
title: Implement accepted ticket-interview improvements
status: paused
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Implement changes 2–4 and the remaining gate from change 6 of the accepted
interview-improvement proposal on `improve-prompt-for-relay-ticket`'s
blackboard (recover it from git history as described in Context). The
original proposal numbers below identify the remaining work. All are edits
to the `bootstrap/ticket` skill text plus tests — no CLI behavior changes:

- **Change 2: Checklist-shaped context question** — replace the Step 3 "what
  will the agent wish they knew?" prompt with concrete buckets:
  files/modules/commands to inspect, related tickets or PRs, constraints and
  out-of-scope lines, known traps, verification commands, safety/rollback.
  One targeted follow-up on a thin answer (code vs docs variants are drafted
  in the proposal).
- **Change 3: Evaluator severity rubric** — Step 6 evaluator assesses the axes
  Objective, Done, Scope, Knowledge, Workflow fit, Safety, and marks each
  finding `must-fix before launch` / `nice-to-have` / `question for human`.
  The authoring agent must resolve must-fix items (edit the body directly, or
  ask the human one concrete question and then edit) before the session ends.
- **Change 4: Thin-answer recovery rule** — never write a blank/title-only
  `## Description`, or a blank `## Context` on a non-concept-capture ticket,
  without one follow-up; deliberate concept-capture stays a workflow-less
  draft with one sentence in the body saying so.
- **Change 6, remaining gate: Conservative Step 4** — create a context/skill
  inline only when the future launched agent needs that exact body. Preserve
  the existing human confirmation of namespace/name and the routing of
  speculative gaps to a `## Proposals` blackboard note.

Done means: the packaged skill text carries changes 2–4 and the exact-body
gate from change 6 while keeping the 4–6-question interview budget;
`tests/test_bootstrap_ticket_skill_template.py` covers the concrete context
buckets, evaluator severity and must-fix resolution, thin-answer recovery,
and the exact-body gate; `python -m pytest` passes.

## Context

**Premise re-checked 2026-09-16 (`adjudicate-parked-and-active-tickets-whose-premise`).**
The subject is alive: changes 2, 3, and 4 are absent from the packaged skill
(its Step 3 context prompt is still "what's the agent going to wish they
knew?", the Step 6 evaluator list carries no severity marking or must-fix
gate, and there is no thin-answer follow-up rule). Two have moved:

- **Change 5 shipped.** The "Ticket format — read this first" section now
  names both layouts (`coga/tasks/<slug>.md` or `coga/tasks/<slug>/ticket.md`)
  and says when each applies. Skip it.
- **Change 6 is partly shipped.** Step 4 already confirms namespace and name
  with the human and routes speculative gaps to a `## Proposals` blackboard
  section. What remains is the gate itself — create a file inline *only* when
  the future launched agent needs that exact body — in place of the current
  "create the file inline rather than leaving it as a TODO" bias.

**The source ticket is retired.** `improve-prompt-for-relay-ticket` was deleted
from `coga/tasks/` after closing (commit `ffb0a383`), so its blackboard is
reachable only through git history:
`git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md`. Its
"Ranked changes" section holds the exact suggested prompt wording for each
change; read it from there.

**Change 1 ("Ask for \"done\" up front") moved out on 2026-09-01.** It is now
owned by `the-ticket-interview-never-asks-what-done-means`, together with the
P2 `## Acceptance Criteria` section this ticket deferred and the parked
`v2/acceptance-criteria` draft — one ticket settles section-vs-sentence rather
than two landing in conflict. **Only changes 2–4 and the exact-body gate from
change 6 remain this ticket's scope.** Skip changes 1 and 5 and preserve the
shipped parts of change 6. If this ticket is unpaused first, leave the
Description/greeting wording to the successor.


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
  section of the retired source ticket's blackboard (git-history pointer
  above) — read it first; the quoted texts are ready to adapt.
- Keep it lean: the skill deliberately targets a 4–6 question interview
  (`product/vision`, `coga/principles`). Refine existing prompts within that
  budget; the Description/greeting change belongs to the successor above.
- Out of scope: a formal `Acceptance Criteria` body section (P2 — deliberately
  deferred); changes to `coga ticket` command behavior unless the text change
  exposes a real CLI mismatch.
- The repo is mid Relay→Coga rename; use Coga wording in any text you touch.
- Verify with `python -m pytest` and eyeball `coga ticket` composing the
  updated skill if practical.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
