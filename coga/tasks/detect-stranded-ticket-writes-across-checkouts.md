---
slug: detect-stranded-ticket-writes-across-checkouts
title: Detect stranded ticket writes across checkouts
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- dev/code
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 2 (evaluate-design)
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
   **Correction found at design (2026-09-09): committed duplicates are already
   *detected*.** `check_branch_contains_control` classifies the ticket path as
   an unsafe overlap and `coga open-pr` refuses — see `### Design-step findings`
   under `## Context`. What is missing is not detection but *discrimination and
   remediation*: the refusal is worded as ordinary branch staleness and tells
   the operator to rebase, which is the one action that converts the stranded
   commit into the merge conflict this residual is about.

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

### What the design concluded

Residual 2 is **already detected and already fail-loud** (see
`### Design-step findings` under `## Context` for the proof and the test that
pins it). The work left on it is small and entirely about wording and timing:

- **Discriminate.** A stranded ticket commit is currently reported as generic
  branch staleness, so the operator cannot tell it apart from a branch that
  simply needs a rebase.
- **Remediate correctly.** The generic message says *rebase*. For a stranded
  ticket commit that is the wrong action — rebasing replays the stranded commit
  onto control and produces exactly the `ticket.md` conflict this ticket exists
  to prevent. The right action is to drop the branch's copy of the ticket and
  take control's.
- **Surface it one step earlier.** The same comparison is available at
  `coga bump` off the implement step, using only refs in the primary checkout —
  no worktree enumeration, no `worktree:` pointer, no cross-filesystem read.

Residual 1 is **not** taken. The headline case it describes — a `## Dev` written
in the feature checkout, leaving the primary copy without linkage — is already
refused by the parent's `requires: branch` gate at the exact moment it happens.
What remains uncovered is stranded blackboard *prose*, which is working memory
rather than linkage, and a general cross-checkout comparator would have to clear
all three of the ticket's hard parts plus the "divergence is the normal state"
wall to catch it. That is not proportionate for a rare, low-stakes residual, so
this ticket takes its own stated fallback and spins residual 1 back to a draft.
See `### Out of scope`.

### Acceptance criteria

- [ ] **A new comparator exists in `src/coga/github_preflight.py`** that returns
      the Coga task/log paths a feature branch has committed which the control
      branch does not contain, distinguishing three states: *some stranded
      paths*, *none*, and *indeterminate* (a git probe failed or a ref is
      missing). Indeterminate is never collapsed into "none" — it follows the
      `git._worktree_holding_branch` / `_WORKTREES_UNKNOWN` precedent.
- [ ] **The comparator does not fire on normal staleness.** A feature copy that
      is merely behind control produces no stranded paths. Verified by a test
      that advances control past the branch without the branch touching the
      task path.
- [ ] **`coga open-pr` reclassifies the freshness refusal.** When
      `check_branch_contains_control` fails and the comparator attributes the
      unsafe overlap to this ticket's own task state, the raised `OpenPrError`
      (a) names the overlapping path(s), (b) gives the command to see the two
      versions, and (c) instructs the operator to restore the branch's copy from
      the control branch and amend/commit — **not** to rebase. The generic
      "Rebase or merge before opening a PR" text is not emitted for that case.
      Non-ticket overlaps keep the existing generic message verbatim.
- [ ] **`coga bump` warns one step earlier.** On a forward bump off a step whose
      blackboard records a usable `branch:`, in the separate-checkout layout,
      bump runs the comparator against the control branch and the recorded
      branch inside `cfg.repo_root` and writes a `[bump]` note to stderr naming
      the stranded path(s) and the fix.
- [ ] **The bump warning is advisory only.** It never blocks the transition,
      never changes the exit code, and never raises — a missing ref, a missing
      branch, an unavailable `git`, or an indeterminate result is silent. It
      does not write to the ticket or to `coga/log.md`.
- [ ] **No false warning in the single-checkout layout.** Where the recorded
      branch is the branch `cfg.repo_root` is standing on, committed task state
      on that branch is the layout working correctly; bump emits nothing. The
      layout test reuses the existing resolver rules rather than new path
      comparison.
- [ ] **open-pr's uncommitted-changes refusal is narrowed.** When
      `git status --porcelain` in the recorded worktree reports dirt inside this
      ticket's own `coga/tasks/<slug>` path, the message steers that dirt to
      *stash or reconcile against the control copy* and explicitly warns that
      committing it strands a duplicate on the branch. Dirt outside the ticket
      path keeps today's "commit or stash them, then relaunch".
- [ ] **No new completion gate.** `STEP_GATES` and `known_gate_tokens()` are
      unchanged; no workflow gains a `requires:` token. The comparison needs
      more than the `check(blackboard_text)` signature provides, so it is a
      bump-side check, not a registry entry.
- [ ] **Existing behavior is preserved.**
      `test_open_pr_rejects_overlapping_coga_state_drift`,
      `test_open_pr_rejects_divergent_ticket_overlap_in_single_checkout`,
      `test_open_pr_accepts_identical_generated_state_overlaps_from_preceding_bumps`,
      `test_open_pr_accepts_non_overlapping_coga_state_drift`, and
      `test_open_pr_rejects_task_rename_overlapping_feature_edit` all still pass
      (the first may be extended to assert the new wording, not weakened).
- [ ] **Tests added:** comparator unit tests for the three states and for the
      merely-behind case; a bump test that warns and one that stays silent in
      the single-checkout layout, mirroring the gate tests in
      `tests/test_commands.py`; an open-pr test for the reclassified message;
      a test for the narrowed cleanliness message.
- [ ] `python -m pytest` is clean and `coga validate --json` is clean against
      `example/`.
- [ ] A `## PR` section is written on the blackboard during implement, because
      `code/open-pr` otherwise falls back to `## Description`, which describes
      only the problem.

### Proposed shape

Four files change. Order of work is 1 → 2 → 3 → 4, each with its tests.

**1. `src/coga/github_preflight.py` — the comparator (new shared helper).**

Add one module-level function beside `check_branch_contains_control`:

```python
def stranded_task_state_paths(
    control_ref: str,
    branch_ref: str,
    *,
    cwd: str | Path | None = None,
    coga_root: str | Path,
) -> tuple[str, ...] | None:
    """Coga task/log paths the branch committed that control does not have.

    Returns the sorted paths that the branch changed since the merge base
    *and* whose blobs differ between the two refs. `None` means the question
    could not be answered (a probe failed, or a ref is missing); callers must
    stay silent rather than read that as "no stranded paths".
    """
```

Implementation reuses what is already in the module — `_run`,
`_coga_root_prefix`, `_changed_paths` (already `--no-renames`, which matters
here for the same reason it matters to the freshness check), and
`_is_coga_state_path`:

1. `git merge-base <control_ref> <branch_ref>` → `None` on failure.
2. `_changed_paths(merge_base, branch_ref)` → `None` on failure; filter to
   `_is_coga_state_path`.
3. For each surviving path, `git diff --quiet <control_ref> <branch_ref> --
   <path>`; keep it when rc is 1 (differs), drop it when rc is 0, return `None`
   on any other rc.

Both conjuncts are load-bearing and neither alone is correct:

- Blob difference alone fires on every well-behaved ticket, because control
  legitimately runs ahead of the feature copy from the first bump onward.
- Branch-side commits alone fire when a bump run from the feature checkout
  committed on the branch and landed byte-identical bytes on control through
  `sync_task_state`'s plumbing path.

Together they mean precisely: *the branch is carrying committed ticket bytes
that control does not have*, which is the merge hazard.

This lands in core rather than at the edge because it has two real consumers
(`open_pr` and `commands/bump`), and because it belongs in the module that
already owns branch-versus-control comparison — no new core module, no new
command, no new gate token. Widen the module docstring's last paragraph to say
the module also owns this comparison; it currently frames itself as auth
preflight plus the freshness probe.

**2. `src/coga/open_pr.py` — reclassify the freshness refusal (`~:442-450`).**

Today a failed `freshness` raises one generic message. Wrap that raise: on
failure, call `stranded_task_state_paths(base_ref, branch, cwd=worktree,
coga_root=cfg.repo_root)`. If it returns a non-empty tuple containing this
ticket's own task path (derive it from `blackboard_path` relative to the
checkout root, the way the `single_checkout` block just above already does),
raise the stranded-write `OpenPrError` instead. Everything else — the `None`
case, an empty tuple, overlaps in other tickets' state — keeps today's message
unchanged.

The new message must carry the correct remediation, roughly:

> Branch `<branch>` has committed changes to this ticket's own task state that
> `<control>` does not contain: `<paths>`. This is a stranded ticket write —
> the ticket was edited in the feature checkout and committed there, while
> `coga` advanced the same file on `<control>`. Rebasing would replay it and
> conflict. Inspect with `git diff <control> <branch> -- <path>`, then take
> control's copy on the branch
> (`git checkout <control> -- <path> && git commit`), or
> `coga block --task <slug> --reason "..."`.

Leave the `single_checkout` carve-out at `:365-371` and
`_single_checkout_publishable_paths` untouched; this only changes which message
a failure produces, never whether it fails.

**3. `src/coga/open_pr.py` — narrow the cleanliness message (`~:373-382`).**

`dirty.stdout` is already in hand. Split its porcelain lines, take the path
field, and test whether any falls under this ticket's task path. If so, append
the stash/reconcile steer to the existing message rather than replacing it, so
mixed dirt (source *and* ticket) still tells the operator to commit the source
half. This is the cheap partial fix the ticket names: it removes the "commit"
instruction that currently manufactures the committed duplicate.

**4. `src/coga/commands/bump.py` — advisory warning after the gate site.**

Immediately after the completion-gate block (`~:192-208`), which has already
read `blackboard` for gated steps, add a small helper call. It must run for
forward bumps whether or not the step declares `requires:`, so read the
blackboard for this purpose when the gate did not
(`read_blackboard(ref.ticket_path, blackboard_required=False)`).

```python
if not rewind:
    _warn_stranded_task_state(cfg, ref, blackboard)
```

The helper, local to the module and wrapped so nothing escapes:

1. `parse_branch_name(blackboard)` (import lazily from `coga.autoclose`, the way
   `step_gate` does, to stay clear of the `validate → autoclose → mark →
   validate` cycle); bail when absent or `(`-prefixed, matching open-pr's
   usability rule.
2. Resolve `cfg.repo_root`'s current branch. If it equals the recorded branch,
   this is the single-checkout layout — return silently. Follow
   `open_pr._checkout_mode` (`~:609`) rather than re-deriving the rule; if its
   signature does not fit a bump caller, extract the branch comparison it uses
   rather than writing a new one.
3. Call `stranded_task_state_paths(cfg.git_control_branch, branch,
   cwd=cfg.repo_root, coga_root=cfg.repo_root)`. `None` or empty → silent.
4. Otherwise write one `[bump]` block to stderr naming the paths and the same
   remediation as the open-pr message. stdout stays untouched — several
   commands parse it.

Cost is bounded: at most three local `git` calls, only on a forward bump, only
when a `branch:` is recorded, and skipped entirely in the single-checkout
layout. Nothing is added to `validate`, which iterates every task and would pay
this per task.

**Tests.** `tests/test_open_pr.py` already builds the exact fixture this needs —
`test_open_pr_rejects_overlapping_coga_state_drift` creates a feature worktree,
commits a task-state file on the branch, and pushes a competing control commit.
Extend it to assert the new wording and add a sibling for the non-ticket overlap
keeping the generic message. Mirror the bump tests on the existing gate tests in
`tests/test_commands.py`.

### Out of scope

- **Residual 1 — the general cross-checkout comparator.** Deliberately dropped
  from this ticket and spun back to a draft, per the ticket's own stated
  fallback and the owner's 2026-09-09 steer. Reasons, so the draft does not
  re-derive them: the primary-copy failure mode is already refused by the
  parent's `requires: branch` gate; the uncovered remainder is stranded
  blackboard prose, which is working memory rather than linkage; and detection
  would need to clear the missing-`worktree:`-pointer case, the invisible
  independent `/tmp` clone, the detached mid-rebase worktree, *and* the fact
  that control-ahead divergence is the normal state — for a rare, low-stakes
  case. If it is revived, the discriminator sketched here (one-directional
  content the other copy lacks) is the part worth keeping.
- **Closing the parent's presence-not-freshness hole.** A stale `## Dev` from an
  earlier attempt still satisfies `requires: branch`. The comparator proposed
  here does not detect it — it compares ticket *bytes*, not whether the recorded
  branch describes the current attempt — so closing that hole is a different
  guard (does the recorded branch exist, does the recorded worktree hold it) and
  belongs in its own ticket. Recorded as an open question for `review-design`
  rather than silently absorbed.
- **Automatic merge or repair of divergent ticket copies.** Report only. The
  operator decides which copy to keep.
- **Refusing the bump.** The bump-side check warns; the hard refusal stays at
  `open-pr`. See the open question on severity.
- **Adding the check to `coga validate`.** It iterates every task; the per-task
  git cost is not worth it for a rare failure.
- **New `requires:` tokens or any change to `STEP_GATES`.**
- Re-litigating the parent's candidate (d) decision; making `coga launch` place
  agents in the recorded worktree (candidate (a) — lives in the two `v2/` draft
  placeholders, do not edit them); retrofitting anything onto existing tickets'
  frozen `workflow:` snapshots.

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

**Owner decision (2026-09-09) — remediation is settled; do not over-engineer
detection.** The owner's steer is that this is a *rare* failure, so the design
should buy detection cheaply rather than optimize for coverage:

- **Report, never repair.** When the check fires it names both copies and shows
  the difference; the operator decides which to keep. That is the whole
  remediation — no auto-merge (see the matching gotcha below), and no blocking
  prompt. The surfaces this check would land on (`bump`, `validate`, `open-pr`)
  run inside launched agent sessions, where a `typer.confirm` would hang the
  supervisor chain; core's only interactive prompts sit in `megalaunch`,
  `uninstall`, and `unblock`, all commands a human types directly. "Ask the
  operator" therefore means *refuse or warn with both paths printed* and let
  the agent escalate — it does not mean prompting. Severity (refuse vs. warn)
  is still open; see the "Fail loud or warn?" gotcha.
- **Spend the design on the discriminator, not on coverage.** Because the case
  is rare, prefer the simplest check that catches the common shape over a
  general cross-checkout comparator. Asking the operator settles *what to do*
  once divergence is found; it does not settle *when to ask*, and that remains
  the hard part, because divergence is the normal state (first gotcha below).
- **Landing residual 2 alone is the preferred outcome, not a consolation
  prize.** If residual 1 cannot be detected cheaply, take the ticket's stated
  fallback — ship the committed-duplicate check and spin residual 1 back to a
  draft — rather than building speculative machinery for a rare case.

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

### Design-step findings (2026-09-09, verified against `main`)

These were established by reading the code during design. They supersede the
"committed ones are not [caught]" premise in `## Description` item 2.

- **Residual 2 is already detected, and already fail-loud.**
  `github_preflight.check_branch_contains_control` (`github_preflight.py:182`)
  computes `overlapping = control_paths & feature_paths`
  (`:274`) — the paths changed on both sides since the merge base — and refuses
  when any overlap is not byte-identical (`unsafe_overlaps`, `:300-316`). A
  ticket edit committed on the feature branch while `coga` advanced the same
  file on control lands in exactly that set, so `coga open-pr` raises
  `OpenPrError` before pushing and before `gh pr create`.
  `tests/test_open_pr.py:879` (`test_open_pr_rejects_overlapping_coga_state_drift`)
  pins this shape today: it asserts `Overlapping paths: coga/tasks/shared.md`.
- **What the operator actually sees is a misdiagnosis.** The refusal renders as
  "current branch does not contain latest <remote>/<control>. Rebase or merge
  before opening a PR, e.g. `git fetch ...` then `git rebase FETCH_HEAD`.
  Overlapping paths: coga/tasks/<slug>.md" (`:317-328`), wrapped by open-pr's
  `Branch <b> is not safe to publish. ... Reconcile it and relaunch`
  (`open_pr.py:448-451`). Following that instruction replays the stranded commit
  onto control and produces the `ticket.md` conflict — **the current remediation
  string is the step that manufactures residual 2's conflict**, the same way the
  cleanliness gate's "commit or stash" does one step earlier.
- **`check_branch_contains_control` has two real consumers**, so it is
  established shared core infra: `open_pr.py:442` and
  `github_preflight.run_preflight` (`:417`), which `validate.py:1449` calls for
  `coga validate --check-github`. Adding a sibling comparator to that module
  creates no new core surface and needs no microkernel argument beyond the one
  the module already satisfies.
- **`github_preflight` imports nothing from `coga`** — only `os`, `subprocess`,
  `dataclasses`, `pathlib`, `urllib.parse`. It is therefore safe to import from
  `commands/bump.py` without touching the
  `validate → step_gate → autoclose → mark → validate` cycle that forces
  `step_gate`'s lazy imports. Import `parse_branch_name` lazily anyway;
  `pr_assist.py:176` is the precedent for a command-side consumer.
- **Reusable private helpers already in the module:** `_run` (20s timeout,
  `None` rc for missing binary or timeout), `_coga_root_prefix` (`:148`, the
  Coga OS root relative to the git toplevel), `_is_coga_state_path` (`:158`,
  `<prefix>/log.md` or `<prefix>/tasks/...`), and `_changed_paths` (`:165`,
  which passes `--no-renames` so a control-side task rename cannot look disjoint
  from a feature-side edit of the old path — the new comparator wants that same
  behavior for the same reason).
- **The early-exit escape.** When HEAD already contains the fetched control tip,
  `check_branch_contains_control` returns ok at `:226-231` without any path
  analysis. A branch that has just been rebased onto control therefore passes
  even while carrying a stranded ticket commit, and the merge is then a clean
  fast-forward that silently overwrites control's later ticket state instead of
  conflicting. This is the second-order path the "rebase" advice above leads to.
  The bump-side warning proposed in `### Proposed shape` fires *before* any
  rebase happens, which is the main reason to place a check earlier than
  open-pr at all. Widening the early exit itself is not proposed here — say so
  if `evaluate-design` thinks it should be.
- **`commands/bump.py` context at the insertion point:** `cfg` is bound at
  `:86`, `ref` at `:91`, `sys` is already imported, and the gate block at
  `:192-208` has already read `blackboard` for gated steps via
  `read_blackboard(ref.ticket_path, blackboard_required=False)`.
- **`STEP_GATES` takes `check(blackboard_text)` only** (`step_gate.py:36`), which
  confirms the ticket's suspicion: a cross-ref comparison cannot be expressed as
  a `requires:` token without changing every gate's signature. The proposal
  keeps the registry untouched.

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


<!-- coga:blackboard -->

## Design pass — 2026-09-09

Spec written into `## Description` (`### What the design concluded`,
`### Acceptance criteria`, `### Proposed shape`, `### Out of scope`) and
`## Context` (`### Design-step findings`). No branch, no code, no PR.

**The finding that reshaped the ticket:** residual 2 is already detected.
`check_branch_contains_control`'s unsafe-overlap rule refuses `coga open-pr`
when the feature branch committed this ticket's own task state and control
advanced the same path; `tests/test_open_pr.py:879` pins it. So the ticket's
"committed ones are not [caught]" premise was wrong, and the real gap is
narrower and cheaper: the refusal is worded as ordinary branch staleness and
prescribes a **rebase**, which is precisely the action that replays the stranded
commit and creates the `ticket.md` conflict. Recommendation is therefore to
discriminate + re-word at open-pr, and run the same comparison one step earlier
at `coga bump` where it costs three local git calls and needs neither worktree
enumeration nor a `worktree:` pointer.

**Residual 1 recommended out**, taking the ticket's own stated fallback: its
headline case is already refused by the parent's `requires: branch` gate, and
the remainder (stranded blackboard prose) does not justify clearing four
blind spots. Reasons recorded in `### Out of scope` so the draft need not
re-derive them.

**Sizing:** one PR. Four files (`github_preflight.py`, `open_pr.py` twice,
`commands/bump.py`) plus tests, with the comparator fixture already built in
`tests/test_open_pr.py`. No split recommended.

**Microkernel:** the comparator joins `github_preflight.py`, which already has
two real consumers (`open_pr`, `run_preflight` via `validate --check-github`)
and already owns branch-versus-control comparison. No new core module, no new
command, no new `requires:` token, no `STEP_GATES` change.

## Open Questions

1. **Severity at `coga bump` — warn or refuse?** The ticket calls this the
   single biggest undecided axis. **Recommendation: warn (stderr, non-fatal,
   never blocks the transition).** The asymmetry that argues for it: if a
   warning is ignored, `open-pr` refuses hard one step later and the cost is one
   wasted step with no data loss; if bump refuses on a false positive, the
   workflow wedges mid-queue and the operator must `coga block` to get out.
   `bump` is also a state transition rather than a network action, and the
   comparator is best-effort by construction. The counter-argument is real and
   the owner should weigh it: the parent shipped a fail-loud refusal at bump,
   and warnings inside launched agent sessions can be ignored. **Owner call.**
2. **Confirm residual 1 is spun back to a draft** rather than attempted here.
   The ticket pre-authorized this outcome and the owner's 2026-09-09 steer
   prefers it; recorded here so the decision is explicit rather than inferred
   from a shorter spec. If confirmed, implement should not create the draft —
   name who does, and whether it reuses one of the parked `v2/` placeholders or
   gets a fresh draft. **Owner call.**
3. **Confirm the presence-not-freshness hole stays out of scope.** The ticket
   asked design to answer rather than absorb it. Answer: the proposed comparator
   does not close it — it compares ticket bytes, not whether the recorded
   `## Dev` describes the current attempt — so closing it is a separate, also
   cheap guard (does the recorded branch exist; does the recorded worktree hold
   it) that belongs in its own ticket. **Owner call on whether to spin that
   ticket now.**
4. **Should the reclassified `open-pr` message print the diff itself, or only
   the command to see it?** Printing it makes a long ticket diff part of an
   error string; open-pr's stdout is a value channel carrying the PR URL alone,
   so any output would go to stderr. **Recommendation: print the command, not
   the diff** — but `evaluate-design` may reasonably prefer a truncated inline
   diff, since the operator here is usually an agent that will not run a
   follow-up command on its own.
5. **Not asked, surfaced by the design:** `check_branch_contains_control`
   returns ok without path analysis when HEAD already contains the control tip
   (`github_preflight.py:226-231`). A branch rebased onto control while carrying
   a stranded ticket commit passes that exit, and the merge then silently
   overwrites control's later ticket state rather than conflicting. The proposed
   bump-side warning fires before any rebase, so it mitigates the path in
   practice, but the exit itself is untouched. **Flagged, not proposed** —
   `evaluate-design`/owner should say whether it wants its own ticket.
