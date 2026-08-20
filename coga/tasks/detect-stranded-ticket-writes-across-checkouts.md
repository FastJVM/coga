---
slug: detect-stranded-ticket-writes-across-checkouts
title: Detect stranded ticket writes across checkouts
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- dev/code
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

Follow-up spun out of `launch-ignores-the-recorded-worktree-stranding-bla`
(see that ticket's design spec and blackboard for the reproduction). That
ticket ships a `requires: dev` completion gate that refuses `coga bump` when
the ticket copy being synced lacks a usable `## Dev` linkage. Two residuals
remain unaddressed, and this ticket covers **both**:

1. **Divergence detection (candidate (c) there).** The gate proves the synced
   copy carries `branch:`/`worktree:`; it does not notice that *another*
   checkout's copy of the same ticket has diverged (e.g. blackboard prose or a
   duplicate `## Dev` written in the feature checkout). A sync-side check —
   bump or validate comparing the ticket blob across linked worktrees /
   the recorded worktree — could surface stranded writes generally. Known
   hard parts: in the primary-copy failure mode there may be no `worktree:`
   pointer to follow; `git worktree list` cannot see independent `/tmp`
   fallback clones; and reconciling divergent free-form markdown needs merge
   semantics.
2. **Committed-duplicate PR conflict.** A stranded ticket edit *committed on
   the feature branch* seeds a `ticket.md` merge conflict when the PR lands
   (the 2026-08-08 PR #90 evidence shape). Uncommitted duplicates are already
   caught by open-pr's cleanliness gate (`open_pr.py:373-383`); committed ones
   are not.

The two residuals share one mechanism — the same ticket file living in two
checkouts with no reconciliation — and one likely detection surface (compare
the ticket blob across the checkouts we *can* enumerate), so they are designed
together. They may still land as two separate guards; deciding that is the
design step's job, not a reason to split the ticket up front.

Done looks like: stranded ticket writes are surfaced by a coga command at a
point where they can still be fixed cheaply, instead of surfacing one step
later as a misleading `open-pr` error or at merge time as a `ticket.md`
conflict. Detection is the goal; automatic merging of divergent markdown is
explicitly *not* assumed to be part of it.

## Context

**Depends on the parent ticket.** `launch-ignores-the-recorded-worktree-stranding-bla`
is `in_progress` at step 2 (`review-design`) as of 2026-08-19 — its
`requires: dev` gate has not landed yet. Before designing, check whether that
gate shipped and what it actually enforces; this ticket's premise is "the gate
exists and is not enough". If the parent changed shape in review, re-read its
`## Proposed Shape` and blackboard rather than trusting the summary above.

Verified code facts (checked 2026-08-19 against `src/coga/` at `main`;
line numbers drift — re-verify before relying on them):

- **Sync entry point.** `git.sync_task_state(cfg, task_path, ...)` at
  `git.py:382`, docstring `:397-422`. It stages only files under the resolved
  task dir (never `git add -A`), and branches on HEAD: control branch → commit
  + push; feature branch → commit on the current branch *and* land the same
  files on control via working-tree-free plumbing; detached HEAD → land on
  control only. Every git failure is non-fatal by design (reported to stderr +
  `log.md`, then swallowed) — a new divergence check must decide deliberately
  whether it inherits that soft-failure model or fails loud.
- **The one-checkout blind spot.** `commands/bump.py:130` syncs `ref.path` —
  the task dir of *the checkout bump ran from*. Nothing looks at any other
  checkout's copy. That is the gap both residuals live in.
- **Existing gate machinery.** `src/coga/step_gate.py` is a deliberately tiny
  registry (`STEP_GATES`, `known_gate_tokens`, `gate_unmet_reason`); its
  docstring frames gates as *data checks* on the blackboard, not exit-code
  checks. The evaluation site is `commands/bump.py:148-163`, forward bumps only
  (rewinds ungated). Note gates today take only `blackboard_text` — a
  cross-checkout comparison needs more than that signature gives, so it is
  probably **not** a new `requires:` token. Say so explicitly in the design
  rather than forcing it into the registry.
- **Cleanliness gate that already exists.** `open_pr.py:373-383` refuses to
  proceed when the recorded worktree has uncommitted changes ("commit or
  stash, then relaunch"). This is what catches an *uncommitted* stranded
  duplicate. Immediately above it (`:365-372`) is the single-checkout carve-out
  that commits the union-safe log first — any new open-pr-side check must not
  break that carve-out or the single-checkout assist layout.
- **Worktree enumeration.** `git worktree list --porcelain` is used in
  `branchsweep.py:287` and `branchcleanup.py:650` — those are the existing
  patterns to copy. It enumerates linked worktrees of *this* repo only, so an
  independent clone (the `/tmp` fallback layout) is invisible to it. Any
  detection built on it is best-effort by construction; the design must say
  what it does *not* cover rather than implying full coverage.
- **`## Dev` parsers.** `parse_branch_name` (`autoclose.py:139`) and
  `parse_worktree_path` (`autoclose.py:163`); open-pr's usability rule for
  `branch:` is "present and not `startswith('(')`" (`open_pr.py:315`).
  `parse_worktree_path` consumers are the blast radius of any change to what
  `worktree:` means: `branchcleanup.py:133`, `open_pr.py:321` and `:589`,
  `commands/retire.py:280`, `commands/launch.py:1573`.

Constraints and gotchas:

- **The pointer is what gets stranded.** In the primary-copy failure mode the
  control ticket has no `worktree:` line to follow — that write is exactly what
  landed in the other checkout. A design that starts "read `worktree:` and
  compare" only covers the cases where the linkage survived. Handle the
  no-pointer case explicitly (git worktree enumeration, branch heuristics, or
  an honest "cannot detect this case").
- **Don't auto-merge.** Reconciling divergent free-form blackboard markdown
  needs merge semantics nobody has specified. Prefer detect-and-report (name
  both copies, show the diff, tell the operator which to keep) over anything
  that rewrites a ticket the operator hasn't seen.
- **Cost per invocation.** If the check lands in `bump` or `validate` it runs
  constantly. Watch shelling out to git per worktree per task; `validate`
  iterates every task.
- **Single-checkout layout must keep working.** Where the primary checkout
  *is* the recorded worktree (`launch.py:469-530`, `:1555-1586`), "two copies"
  is one copy — the check must not report false divergence there.
- **The committed-duplicate residual may want a different surface** than the
  divergence check: it is knowable at open-pr time (does the feature branch's
  `coga/tasks/<slug>/` differ from control's in a way that will conflict?) and
  again at merge time. Consider whether a pre-PR check, a rebase instruction,
  or the existing `resolve-conflicts` bootstrap ticket is the right home.

Repo conventions:

- Read `CLAUDE.md` and the `coga/codebase` context before touching
  `src/coga/` — the microkernel rule decides whether this is shared core infra
  or edge code. The `coga/sync` context (53 KB, not attached — read it in the
  repo) carries `sync_task_state`'s full contract and its failure model; read
  the git-sync sections before changing anything in `git.py`.
- If the fix touches shipped OS files (skills, workflows, contexts under
  `coga/`), mirror the change into the packaged copy under
  `src/coga/resources/templates/coga/` in the same PR.
- Tests live in `tests/`; mirror the existing gate tests in
  `tests/test_commands.py` for anything bump-side. `python -m pytest` and
  `coga validate --json` against `example/` must both be clean.
- **Chicken-and-egg, same as the parent:** this ticket's own implement step
  runs through the path it is fixing. Write `## Dev` from the primary checkout,
  push the branch, and confirm `git show <control-branch>:coga/tasks/<slug>.md`
  carries the `branch:` line before bumping into `open-pr`.

Out of scope: re-litigating the parent's candidate (d) decision; making
`coga launch` place agents in the recorded worktree (candidate (a) — lives in
the two `v2/` draft placeholders, do not edit them); automatic merge of
divergent ticket copies; retrofitting anything onto existing tickets' frozen
`workflow:` snapshots.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
