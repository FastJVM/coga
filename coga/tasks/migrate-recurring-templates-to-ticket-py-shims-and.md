---
slug: migrate-recurring-templates-to-ticket-py-shims-and
title: 'Migrate recurring templates to ticket.py shims and delete recipe:'
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/codebase
- coga/recurring
skills: []
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
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

PR 2 of the script-ticket work: once the classifier from
`recurring-recipe-question` (PR 1) has landed, migrate the five recipe-backed
recurring templates onto `ticket.py` shims, delete the `recipe:` field
entirely, and run the full prose-contract sweep. The authoritative spec is the
parent ticket's **Proposed Shape** — especially *"The recurring shims (PR 2),
concretely"* and *"The split"* — accepted by the owner at `review-design` on
2026-08-18. Do not redesign; execute that spec.

Concretely:

- One eight-line shim per template (no shared dispatcher): `ticket.py` beside
  each of the five recipe-backed templates, importing the core recipe function
  and completing the step via the CLI (`coga bump` subprocess, never an
  in-process Typer call — `OptionInfo` sentinel gotcha).
- `_create_at_slug` copies `ticket.py` from the template directory into the
  created period task directory (only `ticket.py`; other siblings like
  `digest/spool.md` stay with the template).
- Delete `recipe:`: `Template.load`, `Template.recipe`, `DueTask.recipe`,
  `_run_recipe_task`, and both TTY pre-filters (replaced by
  `script_entry_point(...) is not None`).
- Reshape the five one-step workflows and their skills; sync the `digest/post`
  live↔packaged workflow copies (live copy currently missing).
- Prose sweep: `coga/recurring`, `coga/cli`, `coga/sync`, `coga/patterns`,
  `coga/roadmap`, `marketing/positioning`, `README.md`, `docs/vision.md`,
  `docs/concepts.md`, `docs/reference.md`, `docs/market-thesis.md`,
  `docs/cli-extension-audit.md` — plus packaged twins.

## Context

- **Blocked on PR 1.** Do not start until `recurring-recipe-question`'s PR has
  merged; the shims depend on `launch_script.py`, `script_entry_point`, and
  `COGA_TASK_STEP` existing. The intermediate state is coherent: a template
  with `recipe:` and no `ticket.py` keeps taking the old path until this ticket
  lands.
- **Owner decisions already made** (recorded on the parent blackboard,
  2026-08-18): entry point is `ticket.py` exactly; v1 scripts take no operands
  (`sys.argv[1:] == []` — no `COGA_ARG_*` revival); the completion-contract
  classifier (script closes its own step or the agent follows) is the accepted
  rule; `runner.RECIPES` and `coga run` survive unchanged as a public command
  surface.
- **Packaging trap:** packaged template dirs gaining a `.py` file flip from
  "pure data" to "contains Python" — the documented package-walk vs
  `force-include` wheel collision (`coga/codebase`, "Wheel packaging"). Verify
  the wheel builds on a **pristine** clone, not just a dev tree.
- **Tests:** shims are covered from `tests/` by subprocessing the entry point
  against the seeded `example/` fixture — never by collecting the live
  dogfooded `coga/` tree.
- Migrating the ten `runner.RECIPES` implementations out of `src/coga/`, and
  any behavior change to the recipes themselves, stay out of scope — same as
  the parent ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
