---
slug: stop-direct-body-tickets-from-stranding-committed
title: Stop direct-body tickets from stranding committed code off-main
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 3 (pr)
---

## Description

**Problem.** A ticket whose deliverable is *committed source files* was run
under the `direct/body` workflow, which has no branch/push/PR step. The agent
committed the work to a throwaway launch worktree's local branch; coga synced
only the *ticket state* (`ticket.md`/`log.md`) to `main` via its scoped
`git add <task-dir>` (never `git add -A`, by design — see `git.py:100` and
<!-- TODO: sentence truncated in source draft — missing clause between
`git.py:100` and "the never landed"; fill in the sync_task_state rationale -->
the never landed. When the worktree at `.coga/worktrees/<id>/` was deleted, its
branch ref went with it and the commits became unreachable dangling objects.

**Incident (2026-07-06).** `benchmark/run-the-benchmark-baseline` (workflow
`direct/body`, no `## Dev` branch record) produced 5 vendored DaCapo loops
(`loops/{zxing,xalan,luindex,sunflow,avrora}`, 2374 files) that were never on
`main`. Recovered from dangling commits and re-landed via PR #42; the stray
in-repo worktree tombstone was cleaned up and `.coga/worktrees/` gitignored in
`d7863be`. A downstream codex session, finding the loops missing, then tried to
re-vendor them from scratch inside that same fragile in-repo worktree and
crashed when the worktree was torn down under it.

**Root mismatch:** `direct/body` is for side-effect-free / measurement work.
The moment a ticket's deliverable is committed code, "done" and "on `main`" can
silently diverge unless the flow explicitly pushes a branch and opens a PR.

### Objectives

1. **Audit.** Find every ticket whose deliverable is committed files but that
   runs under `direct/body` (start with the `benchmark/` series —
   `extract-slices`, `opus-ladder-comparison-raw-vs-slice`,
   `next-steps-fable-and-annotations`; then sweep the rest of `coga/tasks/`).
   List each with: workflow, whether it commits code, whether a `## Dev`
   branch/PR is recorded.

2. **Remediate the affected tickets.** For each code-producing one, either
   move it to a `code/*` workflow (`code/with-review` / `code/with-self-review`)
   or add an explicit "create feature branch → commit deliverable → push →
   `gh pr create`" step to its body. NOTE the constraint: `workflow:` is frozen
   at creation and is human-owned — for an in-flight ticket this means
   re-authoring via `coga ticket` or a hand-edit followed by
   `coga validate --task <slug>`, not a `coga bump`. Decide per ticket and
   record the choice.

3. **Guardrail against recurrence.** Add a check so a code-producing ticket
   can't silently strand again. Options to weigh (pick one, don't build all):
   - a Dream/REM sweep that flags a `done` ticket whose blackboard names
     committed artifacts (paths under `loops/`, `annotations/`, etc.) that are
     absent from `main`;
   - a convention/lint that `direct/body` tickets must not commit tracked code;
   - ensure launch worktrees are created *outside* the repo per the
     `code/implement` doctrine (`git worktree add ../coga-<branch> ...`) rather
     than inside `.coga/worktrees/` (the in-repo location is what let a stray
     file leak into `main` and made the dir deletable under a live agent).

**Deliverable:** audit table + the remediated tickets (via PR) + the chosen
guardrail, with the design decision for each recorded on the blackboard.

## Context

- Recovery PR for the incident: #42. Cleanup commit: `d7863be`.
- Workflow/sync model: canonical `coga/architecture` + `coga/cli` are composed
  automatically; the scoped-sync rationale is in the bundled `coga/sync`
  context and `coga/.coga/src/coga/git.py` (`sync_task_state`).
- Separately (not this ticket, but related): the `benchmark/*` tickets all
  carry `contexts: []` and don't load the `xpllm/*` protocol contexts — track
  that fix on its own ticket.

<!-- coga:blackboard -->

## Dev

- branch: `direct-body-strand-guard`
- worktree: `/home/n/Code/claude/coga-strand-guard` (external checkout, per
  `code/implement` doctrine — not `.coga/worktrees/`)
- base: `2370bcb2` (merge-base with `main`); implement commit `70c6b81e`
- files: `src/coga/git.py`, `src/coga/mark.py`, `src/coga/commands/mark.py`,
  `tests/test_git.py`, `tests/conftest.py` (+239 lines)

> Reconstructed during self-qa: the `code/implement` step recorded its work
> only in the one-line `log.md` handoff ("see blackboard"), but the blackboard
> itself was never persisted — the notes stranded with the previous session.
> Recovered from git (branch + commit `70c6b81e`) and the log entry.

## Audit (objective 1)

Swept `coga/tasks/` for `direct/body` tickets. Local offenders producing
committed product code that could strand off `main`: **none**.

- `coga/tasks/recurring/dream/ticket.md` — `direct/body`, but Dream is
  side-effect-free analysis/sweep work (no committed product code). Correct
  use of the bodyless flow; no remediation.
- `coga/tasks/cli-extension-model/move-command-logic-to-tickets.md` —
  `direct/body`, already `status: done`. A design/execution ticket; its
  deliverables are skills/script steps, not stranded product trees. Not
  re-audited retroactively (out of self-qa scope); the new guard protects
  future finishes.
- The `benchmark/*` series named in the ticket (`extract-slices`,
  `opus-ladder-comparison-raw-vs-slice`, `next-steps-fable-and-annotations`)
  does **not** exist in this repo — those live in the xpllm/benchmark repo,
  outside this checkout. Nothing to remediate here.

So objective 2 (remediate affected tickets) is a no-op locally — there were no
in-repo code-producing `direct/body` tickets to move to `code/*`.

## Guardrail (objective 3) — chosen: convention/lint via `mark done` refusal

Picked option (b): a deterministic check that refuses to finish a `direct/body`
ticket that committed tracked product code the control branch won't get.

- `git.stranded_product_paths(cfg, anchor)` — three-dot (`base...HEAD`) diff of
  HEAD vs the control branch, `--name-only`, restricted to paths **outside**
  the Coga OS-state subtree. Non-empty ⇒ product code stranded. Fail-open
  (`[]`, never raises) when git is disabled / not a repo / control branch
  absent / HEAD level with base / any probe fails.
- `mark.mark_done(..., force=False)` raises `StrandedProductCode` for
  `_NO_PR_WORKFLOWS` (currently `{"direct/body"}`) when stranding is detected.
- `coga mark done <slug> [--force]` names the paths, points at `code/*`, exits 2.

Why (b) over (a)/(c): (a) Dream/REM sweep is after-the-fact and probabilistic;
(c) external-worktree relocation is a separate, larger launch change (tracked
on its own ticket `auto-persist-dirty-launch-worktrees-...`). (b) is the
smallest deterministic block at the exact moment the strand becomes permanent
(`mark done`), and composes with (c) rather than competing with it.

Known limitation (noted in commit): the guard fires only when `mark done` runs
from the worktree/branch holding the commit; a `mark done` from the primary
checkout (HEAD == control) sees nothing. Acceptable — for `direct/body` the
commit lives in the launch worktree where the transition runs.

## Self-QA

Ran independent `/code-review` + `/simplify` passes against the branch diff
(`direct-body-strand-guard` vs `main`). Both confirmed the detection logic is
correct across the edge cases (HEAD==base, detached HEAD, subdir control-branch
layout, fail-open). Fixes applied and committed as `d8887b31`:

- **simplify:** dropped the redundant `_control_branch_present` pre-check in
  `stranded_product_paths` — `_local_control_base` already covers "control
  branch absent", and this function never fetches/pushes, so it can skip the
  sync helpers' remote-only `ls-remote` probe.
- **code-review (should-fix):** `_mark_script_done` now catches
  `StrandedProductCode` and bails loudly. Currently unreachable (no
  `_NO_PR_WORKFLOWS` member runs as a script), but the set is meant to grow —
  avoids a future traceback from an unattended script launch. `autoclose`'s
  `mark_done` needs no change: it only fires on a *merged PR*, which a no-PR
  workflow can never have, so the guard's workflow-name gate returns early.
- **code-review (should-fix):** added a detached-HEAD launch-worktree
  regression test — the actual production trigger, previously only covered via
  named feature branches.
- **code-review:** switched the detector diff to `-z` so non-ASCII product
  paths are named verbatim in the `mark done` error (the guard's whole UX is
  naming the offending paths), matching `_changed_paths_under`.

Left for the human reviewer (optional/nits): hoisting `_workflow_name` onto
`Ticket` as a property (single caller today).

Tests: full suite `1093 passed, 1 skipped` (the one environmental
`test_bootstrap_script_launch_is_stateless` failure is a sandbox artifact —
no editable install, so a spawned subprocess can't import `coga`; it fails
identically on the pre-QA base and passes with `PYTHONPATH=…/src`).
