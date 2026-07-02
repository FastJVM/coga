---
slug: branch-cleanup-as-recurring-tasks
title: branch cleanup as recurring tasks
status: active
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
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
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Build a recurring **branch sweep**: a script-mode job that deletes local and
remote git branches whose work has already landed, as a safety net behind the
retire-time deletion that `src/coga/branchcleanup.py` now performs. Retire
handles the common path, but its cleanup is best-effort (git/gh failures are
swallowed), and branches also leak when a ticket is deleted without going
through retire or a session dies mid-flight. The sweep's first run also prunes
the merged part of the pre-existing backlog (~10 local / ~29 remote stale
branches accumulated before retire-time deletion shipped); abandoned no-PR
branches are skipped-and-reported by design and may need one manual pass.

Model it 1:1 on `autoclose-merged`, which is the shape to copy end to end:

1. New sweep function (e.g. `src/coga/branchsweep.py`, mirroring
   `autoclose.sweep_merged` and reusing `branchcleanup.py`'s delete helpers):
   enumerate actual local and `origin` branches and delete the ones that are
   safe (gates below). No ticket-matching guesswork — the gate is GitHub, not
   Coga state.
2. Script skill `coga/skills/coga/branch-sweep/sweep/SKILL.md` with
   `script: run.py` that imports and calls the sweep function directly
   (same pattern as `coga/autoclose/sweep`).
3. One-step script workflow `coga/workflows/branch-sweep/sweep.md`
   (same shape as `autoclose-merged/sweep`).
4. Recurring task `coga/recurring/branch-sweep/ticket.md` with
   `autonomy: auto` and a weekly schedule (retire handles the daily flow;
   weekly is enough for leaks).

Because the runnable unit is the workflow + script skill, the sweep runs
**both ways**: on schedule via `coga recurring`, on demand via
`coga recurring launch branch-sweep`, or as a standalone one-off ticket that
sets `workflow: branch-sweep/sweep`. Note that in the recurring ticket's body.

**Deletion gates (all must hold):**

- Never `main` (the control branch), never the currently checked-out branch
  (git already refuses branches checked out in any worktree).
- Skip any branch recorded under a live (not-`done`) ticket's blackboard
  `## Dev` `branch:` line — a mid-workflow merged PR must not lose its branch
  while the ticket is still moving (autoclose treats those as suspicious for
  the same reason).
- **Remote** delete only when GitHub reports a **merged** PR for that head
  branch **and no open PR** (`gh pr list --head <branch>` with
  `--state merged` non-empty and `--state open` empty — by branch name, no
  ticket needed). The no-open-PR condition closes the branch-reuse hole: a
  branch that once merged a PR and was later reused for a new open PR must
  survive. Do not use ancestry: squash-merge leaves the tip a non-ancestor of
  `main`. Deleting `origin/<branch>` is not reflog-protected, so merged-PR is
  the only authorization.
- **Local** delete follows `branchcleanup.py`'s existing policy: prefer
  `git branch -d`; if that refuses but the PR merged (squash case), log the
  tip SHA then `-D`; unmerged with no merged PR → skip and report.
- `gh` missing/unauthed → skip gated deletes and report, never force.

Out of scope: changing retire-time deletion, and the autocommit idea from the
sibling ticket (`handle-better-delete-branches-autcommit`) — still its own
future ticket.

## Context

- `src/coga/branchcleanup.py` is the retire-time deleter — read its module
  docstring for the full safety model; reuse its local/remote delete helpers
  rather than duplicating them. Note they are private (`_delete_remote`,
  `_delete_local`) and shaped around a single ticket — decide between
  importing them or a small refactor to export them, and note the choice on
  the blackboard. `src/coga/autoclose.py` has `parse_branch_name()` (already
  normalizes the inconsistent `branch:` forms: bare, `- ` list item,
  backtick-wrapped) — use it for the live-ticket skip-list instead of a new
  regex; enumerate not-`done` tickets the same way `sweep_merged()` does.
  Its `pr_state()` is URL-keyed and does **not** cover the by-branch-name
  gate — write a new small gh helper for `gh pr list --head`.
- The model to copy: recurring ticket `coga/recurring/autoclose-merged/`,
  workflow `coga/workflows/autoclose-merged/sweep.md`, script skill
  `coga/skills/coga/autoclose/sweep/` (SKILL.md + run.py).
- **Packaged-copy sync checklist** — each new file has a shipped twin; add
  both or `coga init` drifts from this repo:
  - `coga/recurring/branch-sweep/` ↔
    `src/coga/resources/templates/coga/recurring/branch-sweep/`
  - `coga/workflows/branch-sweep/` ↔
    `src/coga/resources/templates/coga/workflows/branch-sweep/`
  - `coga/skills/coga/branch-sweep/` ↔
    `src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/`
- Tests: follow `tests/test_branchcleanup.py` (real temp git repo + bare
  origin) and `tests/test_autoclose.py`. Cover at minimum: squash-merged
  branch deleted, open-PR branch skipped, no-PR branch skipped,
  live-ticket branch skipped, `main`/checked-out never touched, `gh`
  unavailable → no deletes.
- History: retire-time deletion was ticket
  `handle-better-delete-branches-autcommit` — its blackboard has the design
  rationale (ancestry vs PR-merged gating) and the evaluator review that
  killed the earlier ticket-matching sweep design; this ticket's gh-by-branch-
  name gate is the answer to that objection.

<!-- coga:blackboard -->
## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.
