---
title: The period-task context never covers the deterministic ticket.py firing
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 2 (peer-review)
---

## Description

`src/coga/recurring.py` auto-attaches `coga/period-task` to **every** period
task unconditionally — the create path even strips a hand-added duplicate. But
five of the seven shipped templates (`autoclose-merged`, `blocker-reminders`,
`branch-sweep`, `digest`, `skill-update`) carry the reserved `ticket.py`
sibling, and `coga/contexts/coga/recurring/SKILL.md` states plainly that for
those "no agent starts"; their skills each repeat "no agent, no composed
prompt".

The context is written end to end for an agent — "You are a period task", "read
the blackboard region … to find where the previous run stopped", "finish the
current workflow step with `coga bump` — or `coga mark done` when your
workflow's only step is `direct/body`" — and nowhere says that for a `ticket.py`
template the recipe performs that bookkeeping in code and no reader of this
context exists.

The corpus shows the consequence: a committed sweep run-log records three
completed deterministic runs whose period blackboards contain nothing but the
untouched seeded placeholder.

## Context

Add a short section to `coga/contexts/coga/period-task/SKILL.md` and its
enforced packaged twin under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/`
distinguishing the agent-backed firing from the deterministic `ticket.py`
firing, so the parent-blackboard state contract reads as "whoever runs this
period, agent or recipe" rather than as instructions to an agent that is never
spawned.

Two neighbouring items land in the same area and are already routed this Dream
run — a proposal PR correcting the recurring context's `ticket.py` dispatch
description (it is not binary; a hybrid script chains into an agent phase), and
the sibling ticket `define-the-recipe-reporting-contract-report-durabi`. Read
both before writing so the three agree on one story.

<!-- coga:blackboard -->

## Dev

branch: period-task-recipe-firing
worktree: /home/n/Code/claude/coga-period-task-recipe-firing

## Plan

Single knowledge change, no code: add a section to `coga/contexts/coga/period-task/SKILL.md`
(+ enforced packaged twin) naming who runs a period — an agent, or the template's
`ticket.py` — and reframing the rest of the context as addressed to whichever one it is.
Tradeoff taken: a short framing section near the top rather than rewriting every "you"
in the file, so the existing agent-facing prose stays intact and the twin diff stays small.

## Findings

- The "proposal PR correcting the recurring context's `ticket.py` dispatch description"
  named in `## Context` is PR #774 (`a2028a7d`), already merged: `coga/recurring` now says
  `ticket.py` selects a deterministic *phase*, with `run_script_chain`
  (`src/coga/launch_script.py`) deciding after exit whether an agent follows. The new
  section defers to that bullet and the completion contract rather than restating them.
- Sibling `define-the-recipe-reporting-contract-report-durabi` is still `draft`. Its
  Part 1 (period blackboard is per-run for recipe code too) is consistent with the new
  section, which says the period blackboard is scratch regardless of reader and that an
  untouched seeded placeholder is the normal signature of a deterministic run. Nothing
  written here pre-empts its Part 2 (durable failure surface).
- Ticket counts are stale: the daily digest was removed (#786), so the shipped set is now
  six templates, four with `ticket.py` (`autoclose-merged`, `blocker-reminders`,
  `branch-sweep`, `skill-update`). The context deliberately names the pattern, not the
  templates, so it does not drift with that count.
- Code facts cited: `_create_at_slug` (`src/coga/recurring.py`) appends `coga/period-task`;
  `_template_frontmatter` strips a copy a promoted template already carries.
  `mark.mark_done` reads the period's `.state-snapshot.json` itself, so the `state_keys`
  check fires for a script's shell-out `coga bump`/`coga mark done` the same as an agent's
  (`_warn_if_state_not_advanced` in `src/coga/mark.py`). `COGA_TASK_BLACKBOARD`
  (`task_env.build_task_env`) points at the *period* ticket, never the parent, which is
  why the section says the recipe reads/writes the parent blackboard by its own path.

## Changes

- `coga/contexts/coga/period-task/SKILL.md` + packaged twin (byte-identical):
  - frontmatter `description` now names both readers;
  - new section `## Who runs this period: an agent, or the template's ticket.py` — the
    two dispatch shapes, the non-binary chain-to-agent case, "read the rest as addressed
    to whoever runs this period", and the placeholder-blackboard consequence;
  - step 3 of the state shape and the `state_keys` paragraph note that a `ticket.py`
    closes its own step via the CLI and is checked the same way.
- No fixture change: no task layout, prompt composition, or workflow semantics changed.

## Verification

- `tests/test_packaging.py`, `tests/test_period_state.py`, `tests/test_recurring.py`: 388 passed.
- Full `python -m pytest` (worktree `src` on `PYTHONPATH`, primary `.venv` 3.12): 2495 passed.
- Branch contains `origin/main` (fetched before commit; no new commits since).
