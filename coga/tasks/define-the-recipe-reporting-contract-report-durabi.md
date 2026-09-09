---
slug: define-the-recipe-reporting-contract-report-durabi
title: 'Define the recipe reporting contract: report durability and failure surface'
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 1 (implement)
---

## Description

Two halves of one missing contract for deterministic `ticket.py` recipes,
which are five of the seven shipped recurring templates.

**1. Nobody records that a recipe's report blackboard is per-run.** Coga states
the "period blackboards are scratch" rule twice for *agents* —
`coga/contexts/coga/period-task/SKILL.md` ("nothing in your task directory
survives to the next firing") and the recurring context's Gotchas — but nowhere
for *recipe code*, which reaches the same file through `COGA_TASK_BLACKBOARD` /
`coga.task_env.blackboard_from_env`. The knowledge that does exist covers only
containment: `coga/contexts/coga/codebase/SKILL.md` says the helper "refuses a
blackboard outside the `tasks/` tree of the root the recipe is operating on" —
i.e. *which repo*, never *which task and for how long*. Four shipped recipes
append reports through it (`src/coga/autoclose.py`, `src/coga/dream_validate_drift.py`,
`src/coga/dream_cleanup_orphan_markers.py`, `src/coga/skill_update.py`), and
under a recurring template every one resolves to
`coga/tasks/recurring/<name>/ticket.md`, which the next firing deletes. Three
are correct because their durable output is a PR or a run summary; autoclose's
retire follow-up was not, and `render_retire_report`'s docstring claiming the
target was "a long-lived recurring task's blackboard" is recorded as exactly why
that bug survived review. `digest-can-clobber-recurring-last-serviced-period`
is the same class from another angle.

**2. A failing recipe's detail reaches no durable surface, and nothing owns the
rule.** It is stated only in a source docstring: `run_skill_update_recipe`
(`src/coga/skill_update.py`) documents that both non-zero exits leave a
`## Skill Update` section on the blackboard "rather than to stderr alone, which
the recurring sweep discards", then names the debt itself — "the first instance
of a property the other recipes still lack — `dream_validate_drift`,
`dream_cleanup_orphan_markers`, `branchsweep`, `autoclose`, `blocker_reminders`
and `recurring_autofix` all exit non-zero to stderr alone. It belongs in the
recipe layer rather than here; do not paste a seventh copy, generalize it
instead." Nothing in `coga/contexts/coga/recurring/SKILL.md` carries this, and
no ticket owns the generalization. Two independently filed tickets show the
cost: `autofix/stop-the-digest-spool-drain-leaking-a-blank-line-e` ("The job
exits 0 and posts correctly, so nothing in the sweep reports it — this is a
silent, monotonic growth leak in a git-tracked state file") and
`recurring-sweep-wedges-on-the-ticket-py-it-copies` ("Nothing increments a
problem counter, so the sweep still exits `problems: 0`").

## Context

Part 1 is a paragraph for recipe authors, in the recurring or codebase context
(with its enforced twin): `blackboard_from_env` is a per-run reporting surface,
not durable storage; anything that must outlive the period goes to the
template's own blackboard, a template sibling file (the `recurring/digest/spool.md`
precedent, and the `retires.md` proposed by `persist-autoclose-retire-follow-ups`),
or the repo-global `coga/log.md`.

Part 2 is the generalization the docstring asks for — the recipe layer owning
"a failing recipe writes its detail to a durable surface" once, rather than a
seventh pasted copy — plus stating that contract in the recurring context.

Related and already routed this Dream run: a proposal PR corrects the recurring
context's claim that the blackboard is where every `ticket.py` phase writes what
it found (four of five shipped templates write nothing). Check it before editing
the same section.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
