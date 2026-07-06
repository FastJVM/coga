---
slug: stop-direct-body-tickets-from-stranding-committed
title: Stop direct-body tickets from stranding committed code off-main
status: draft
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
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
