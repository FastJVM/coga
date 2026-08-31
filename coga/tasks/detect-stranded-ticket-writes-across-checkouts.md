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
ticket shipped a `requires: branch` completion gate that refuses `coga bump`
when the ticket copy being synced lacks a usable `## Dev` linkage. Two
residuals remain unaddressed, and this ticket covers **both**:

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
   (the 2026-08-08 PR #90 evidence shape — **external repo, not inspectable
   from this checkout**; see the parent's `## Context`, and do not go looking
   for PR #90 here). Uncommitted duplicates are already caught by open-pr's
   cleanliness gate (`open_pr.py:373-382`); committed ones are not. Note this
   residual needs no checkout enumeration and no `worktree:` pointer: both
   sides are refs in one repo, so the whole comparison is
   `git show <control-branch>:coga/tasks/<slug>.md` against the feature tip,
   and `branch:` is already validated by open-pr before that path runs.

The two residuals share a *cause* — the same ticket file living in two
checkouts with no reconciliation — but do not assume they share an
implementation: residual 1 compares working trees across filesystems at
deliberately-unequal points in their sync histories, while residual 2 compares
two branch tips in one repo. Residual 2 hits none of residual 1's three hard
parts.

The strongest reason to design them together is that **the existing
remediation converts the first into the second.** open-pr's cleanliness gate
tells the operator "Commit or stash them, then relaunch"; an agent that takes
the *commit* branch commits the stranded duplicate onto the feature branch and
thereby manufactures exactly the `ticket.md` merge conflict residual 2
describes. One designer should see both ends of that pipeline. (A cheap partial
fix falls out of it: narrow that message so a dirty `coga/tasks/<slug>/`
specifically is steered to *stash* or reconcile, not to *commit*.)

They may still land as two separate guards, and **landing residual 2 alone in
this PR is an acceptable, non-failing outcome** if the design concludes the
surfaces genuinely diverge — spin residual 1 back to a draft rather than
holding the easy win hostage to the speculative one. Note this couples to the
microkernel question: a comparator called from bump, validate, *and* open-pr
plausibly clears the ≥2-real-consumers bar for `src/coga/`, whereas an
open-pr-only check is a single consumer and belongs beside the ticket or skill
that uses it.

Done looks like: stranded ticket writes are surfaced by a coga command at a
point where they can still be fixed cheaply, instead of surfacing one step
later as a misleading `open-pr` error or at merge time as a `ticket.md`
conflict. Detection is the goal; automatic merging of divergent markdown is
explicitly *not* assumed to be part of it.

## Context

**The parent ticket has landed.** `launch-ignores-the-recorded-worktree-stranding-bla`
is `done`; its PR (#709, branch `implement-branch-gate`) merged 2026-08-25. The
gate it shipped is `requires: branch` — **not** `requires: dev`, which is what
this ticket's earlier drafts called it. So the premise "the gate exists and is
not enough" now holds literally: read `src/coga/step_gate.py` and the parent's
`## Proposed Shape` / blackboard before designing.

Note what the shipped gate already does in *prose*: its `branch` remediation
string explicitly tells the operator that a `## Dev` written from inside the
feature checkout landed in that checkout's copy, and warns that a stale `## Dev`
from an earlier attempt satisfies the gate while stranding the current one. That
covers the operator-facing explanation. What is still missing is *detection* —
nothing compares the copies. Do not re-spend the design on re-explaining the
failure mode; spend it on whether and where it can be detected.

Verified code facts (re-checked 2026-08-31 against `src/coga/` at `main`;
line numbers drift — re-verify before relying on them):

- **Sync entry point.** `git.sync_task_state(cfg, task_path, ...)` at
  `git.py:597`, docstring `:617-...`. It stages only files under the resolved
  task dir (never `git add -A`), and branches on HEAD: control branch → commit
  + push; feature branch → commit on the current branch *and* land the same
  files on control via working-tree-free plumbing; detached HEAD → land on
  control only. Every git failure is non-fatal by design (reported to stderr +
  `log.md`, then swallowed) — a new divergence check must decide deliberately
  whether it inherits that soft-failure model or fails loud. Its keyword
  surface grew with the parent's work (`publish_current_branch`,
  `feature_publication` lease + guard, `generated_paths`,
  `raise_state_regression`); read the current signature, not this summary.
- **The one-checkout blind spot.** `bump` is split across two modules: the
  Typer command is `commands/bump.py`, and the movement logic is
  `src/coga/bump.py`. The sync is the `sync_state()` closure at
  `src/coga/bump.py:191-225`, which passes `ref.path` — the task dir of *the
  checkout bump ran from*. Nothing looks at any other checkout's copy. That is
  the gap both residuals live in.
- **Existing gate machinery.** `src/coga/step_gate.py` is a deliberately tiny
  registry (`STEP_GATES`, `known_gate_tokens`, `gate_unmet_reason`,
  `gate_publishes_current_branch`); its docstring frames gates as *data checks*
  on the blackboard, not exit-code checks. Two tokens are registered: `branch`
  (the parent's gate — requires a usable `branch:` **and** `worktree:`) and
  `pr`. The evaluation site is `commands/bump.py:192-208`, forward bumps only
  (rewinds ungated). Note gates still take only `blackboard_text` — a
  cross-checkout comparison needs more than that signature gives, so it is
  probably **not** a new `requires:` token. Say so explicitly in the design
  rather than forcing it into the registry.
- **Cleanliness gate that already exists.** `open_pr.py:373-382` refuses to
  proceed when the recorded worktree has uncommitted changes ("commit or
  stash, then relaunch"). This is what catches an *uncommitted* stranded
  duplicate. Immediately above it (`:365-371`) is the single-checkout carve-out
  that commits the union-safe log first — any new open-pr-side check must not
  break that carve-out or the single-checkout assist layout.
- **Worktree enumeration.** The only two `git worktree list --porcelain`
  call sites in `src/coga/` are `branchsweep._worktree_branches`
  (`branchsweep.py:306`) and `git._worktree_holding_branch` (`git.py:4931`) —
  those are the patterns to copy. (`branchcleanup.py` does *not* enumerate
  worktrees at all; see the blind-spot constraint below for what its `:650`
  comment actually says.) Closest precedent for a *core* consumer is
  `git._worktree_holding_branch` (`git.py:4922`), which enumerates worktrees and
  returns a `_WORKTREES_UNKNOWN` sentinel distinguishing "listing failed" from
  "no worktree holds the branch" — reuse that three-state shape rather than
  collapsing failure into absence. Enumeration sees linked worktrees of *this*
  repo only, so an independent clone (the `/tmp` fallback layout) is invisible
  to it. Any detection built on it is best-effort by construction; the design
  must say what it does *not* cover rather than implying full coverage.
- **Same-checkout identity.** `open_pr.same_git_checkout(left, right)`
  (`open_pr.py:84`) and `git.is_linked_worktree(start)` (`git.py:5098`) already
  answer "are these the same checkout / is this a linked worktree". These are
  the ready-made guards against reporting false divergence in the
  single-checkout layout; prefer them over new path comparison.
- **`## Dev` parsers.** `parse_branch_name` (`autoclose.py:206`) and
  `parse_worktree_path` (`autoclose.py:224`), plus `parse_pr_url` (`:166`);
  open-pr's usability rule for `branch:` is "present and not
  `startswith('(')`" (`open_pr.py:312-313`). `parse_worktree_path` has seven
  consumers across `open_pr`, `branchcleanup`, `retire`, `launch`, `step_gate`,
  and `autoclose` (and `parse_branch_name` also feeds `pr_assist.py:176`); grep
  before changing their semantics — this ticket *reads* `worktree:`, it does not
  redefine it, so it should not need to.

Constraints and gotchas:

- **Divergence is the normal state, not the symptom.** This is the constraint
  that bounds the whole design, so read it before anything else.
  `git.sync_task_state`'s feature-branch path commits the task dir on the
  current branch *and* lands the same files on control. But the flow
  `code/implement` actually mandates — write `## Dev` in the primary checkout,
  run `coga bump` from the primary checkout — takes the *control-branch* path,
  which updates control only. Nothing ever pushes those files back into the
  feature worktree's working tree: `git._try_update_local_ref`
  (`git.py:4877-4914`) is core's only cross-checkout ref reconciler, and it
  deliberately fast-forwards **only** the checkout holding the *control* branch
  (via `git merge --ff-only` inside that worktree, so ref, index, and working
  tree move together). A worktree holding a different branch is never touched
  by any path. So from the first bump onward the feature checkout's
  `coga/tasks/<slug>.md` is *expected* to be stale relative to control, and the
  gap widens with every later bump, `log.md` append, and unrelated sync.
  **A check built on blob inequality would fire on every well-behaved code
  ticket in the repo.** Detection needs a discriminator for *which* divergence
  is stranding — the most promising is one-directional content loss (the
  feature copy carries `## Dev` linkage or blackboard prose that the control
  copy *lacks*); "feature copy is merely behind control" must stay silent.
  `_try_update_local_ref` is also the closest precedent for the *problem* — it
  is core's worked answer to "this file lives in two checkouts, reconcile
  carefully," and its stance (ff-only, refuse divergence, refuse to overwrite
  local edits, report non-fatally) aligns with the don't-auto-merge rule below.
- **Enumeration has a fourth blind spot.** Beyond independent `/tmp` clones and
  the missing-pointer case, a worktree mid-rebase or mid-bisect reports as
  *detached*, so its branch is invisible to both `git worktree list --porcelain`
  and `%(worktreepath)`. That is documented in the comment at
  `branchcleanup.py:645-653`, which explains why branch cleanup uses
  `git branch -D` rather than `update-ref` plumbing. Do not cite that comment as
  an enumeration pattern — it is the argument that enumeration is *insufficient*.
  It makes the best-effort framing more correct, not less: say what the check
  does not cover instead of asserting coverage.
- **Fail loud or warn?** Decide this explicitly, independent of where the check
  lands. `validate` is a lint, `bump` is a state transition, `open-pr` is a
  network action, and the parent shipped a fail-loud refusal — these pull in
  different directions. This is the single biggest undecided axis; do not let
  it be inferred from the surface choice.
- **The parent's presence-not-freshness hole.** The parent explicitly left the
  `branch` gate presence-based: a stale `## Dev` from a prior attempt satisfies
  it while the current attempt strands. A cross-checkout comparator is the
  natural mechanism for closing that (comparing copies is exactly how you
  notice control's `## Dev` names a different branch than the feature checkout
  is on). This ticket does **not** pre-decide whether that is in scope — the
  design step should answer it and put the answer to the owner at
  `review-design`, rather than silently absorbing it.
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
  *is* the recorded worktree, "two copies" is one copy — the check must not
  report false divergence there. `open_pr._checkout_mode` (`open_pr.py:609`)
  is the existing resolver for that `(single_checkout, refusal)` decision, and
  `commands/launch.py:2630-2656` is the launch-side analogue; follow their
  rules rather than re-deriving them.
- **The committed-duplicate residual may want a different surface** than the
  divergence check: it is knowable at open-pr time (does the feature branch's
  `coga/tasks/<slug>/` differ from control's in a way that will conflict?) and
  again at merge time. Consider whether a pre-PR check, a rebase instruction,
  or the existing `resolve-conflicts` bootstrap ticket is the right home.

Repo conventions:

- Read `CLAUDE.md` and the `coga/codebase` context before touching
  `src/coga/` — the microkernel rule decides whether this is shared core infra
  or edge code. The `coga/sync` context (57.8 KiB, not attached — read it in the
  repo) carries `sync_task_state`'s full contract and its failure model; read
  the git-sync sections before changing anything in `git.py`.
- If the fix touches shipped OS files (skills, workflows, contexts under
  `coga/`), mirror the change into the packaged copy under
  `src/coga/resources/templates/coga/` in the same PR.
- Tests live in `tests/`; mirror the existing gate tests in
  `tests/test_commands.py` for anything bump-side. `python -m pytest` and
  `coga validate --json` against `example/` must both be clean.
- **Chicken-and-egg — and unlike the parent, you are gated.** This ticket's own
  implement step runs through the path it is fixing. The parent's `implement`
  was genuinely unguarded (its workflow froze before the gate existed, and the
  owner declined to retrofit it); this ticket's `workflow:` is still an
  unfrozen bare string, so activation freezes it from the packaged template,
  which declares `requires: branch` on `implement`. Expect the refusal — it is
  the tool working, not the ticket being wrong. The advice still stands anyway,
  because the gate is presence-based and cheaply satisfiable: write `## Dev`
  from the primary checkout, push the branch, and confirm
  `git show <control-branch>:coga/tasks/<slug>.md` carries the `branch:` line
  before bumping into `open-pr`.
- **Write a `## PR` section on the blackboard during implement.** This workflow
  has no peer-review step, and `code/open-pr` falls back to `## Description` for
  the PR body — which here describes only the *problem*, so the PR would explain
  the bug and never the fix. The parent hit this and recorded the same
  instruction.

Out of scope: re-litigating the parent's candidate (d) decision; making
`coga launch` place agents in the recorded worktree (candidate (a) — lives in
the two `v2/` draft placeholders, do not edit them); automatic merge of
divergent ticket copies; retrofitting anything onto existing tickets' frozen
`workflow:` snapshots.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
