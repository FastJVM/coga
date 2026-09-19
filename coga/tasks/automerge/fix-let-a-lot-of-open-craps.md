---
title: fix let a lot of open craps
status: in_progress
owner: nicktoper
agent: claude
contexts:
- dev/code
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
step: 4 (review)
---

## Description

Merged tickets leave their worktrees and branches behind. The daily autoclose
sweep (`coga run autoclose`, fired by `coga/recurring/autoclose-merged/`)
marks a merged final-step ticket `done` but never disposes of its checkout:
it only writes a `coga retire <slug>` follow-up into
`coga/recurring/autoclose-merged/retires.md` and waits for a human to type it.
Nobody does. The worklist holds ten open entries, and the clone that runs the
recurring jobs (`/home/n/Code/claude/coga`, the editable `uv` install) has 45
linked worktrees — the ten recorded ones plus dozens of ad-hoc review and
scratch checkouts no ticket ever recorded. The weekly branch sweep cannot take
any of them: it preserves every branch a live worktree pins
(`skipped-worktree-pinned`).

Fix both halves, deterministically, no agent in the loop:

**Daily — autoclose disposes of what it closes.** After `sweep_merged` marks
a ticket done, remove the ticket's recorded linked worktree, then delete its
local branch, then its `origin` branch, under exactly the proofs `coga retire`
runs today (`branchcleanup.remove_ticket_worktree`,
`branchcleanup.delete_ticket_branch`). On every recurring run also walk the
open `retires.md` entries and apply the same proofs to each recorded
branch/worktree, so the existing backlog drains without ten hand-typed
retires. Anything a proof refuses stays on the worklist with its reason;
`coga retire` keeps working unchanged for the manual path, and both callers
share one implementation.

**Weekly — branch sweep GCs what no ticket links.** Extend
`branchsweep.sweep_branches` so a landed branch held by a live worktree is no
longer `skipped-worktree-pinned`: if that worktree is a linked worktree of
this repo, checked out on that branch, locally pristine (no modified tracked
or untracked files; ignored caches are fine), and claimed by no non-terminal
ticket, remove the worktree first and then delete the local and remote branch
under the sweep's existing landed-branch authorization. Worktrees that fail
any of those proofs are reported with the reason, as today.

**Make the assumption explicit.** Removing an unrecorded worktree rests on
one repo-level assumption: every linked worktree of this repository belongs
to a Coga ticket, so a landed, pristine one nobody claims is finished work,
not someone's scratch checkout. Declare it as a `[git]` setting in
`coga.toml` (new key, e.g. `worktrees_ticket_owned = true`, default `false`),
gate the weekly worktree GC on it — off, the sweep keeps today's
`skipped-worktree-pinned` — and write the assumption down in the context that
owns the checkout convention.

Done means: on the recurring clone, one `coga run autoclose` closes and
disposes of every recorded checkout the proofs admit and drains the worklist
down to preserved entries with reasons; one `coga run branch-sweep` removes
every pristine landed worktree and its branches; `coga/autoclose/sweep`,
`coga/branch-sweep/sweep`, both recurring ticket texts, and the
`retire_worklist.RETIRE_WORKLIST_HEADER` constant describe the new behavior;
tests cover dispose / preserve / backlog-drain / remote-delete /
worktree-GC (key on and off) paths and `coga retire` after the
shared-function move.

## Context

**Which clone runs the jobs.** Recurring jobs run from
`/home/n/Code/claude/coga` (the `uv tool` editable install; it holds
`.coga/recurring-runs`). Both sweeps only ever touch worktrees linked to the
clone they run from — `branchcleanup._is_linked_worktree_of` preserves
anything else as an independent clone — so state that in the skill text. The
ten worklist entries point at `/home/n/Code/claude/coga-<branch>` worktrees of
that clone, so the drain will find them there. Other clones (this one at
`/home/n/Code/coga` has seven stale `/tmp/coga-pr*-review` review worktrees)
need their own `coga run branch-sweep`.

**Where the sweeps live.** `autoclose.sweep_merged` scans tickets,
`autoclose._try_bump_one` closes one, and `autoclose._report_retire_followups`
is where the follow-up is named today and the worklist reconciled via
`retire_worklist.reconcile_worklist`; `retire_worklist.parse_worklist` /
`is_discharged` / `discharge_slug` own the worklist file format — reuse
them. `branchsweep.sweep_branches` enumerates worktrees and branches and
already runs the landed-branch proofs (`local_branch_landed`, merged-PR
authorization); the pinned-worktree skip is the one branch to change. Both
period tasks' `ticket.py` run through `runner.run_recipe`, so each sweep
stays a registered `coga run` recipe with a stable argv/stdout/exit contract.

**Where the proofs live.** `branchcleanup.remove_ticket_worktree` (same-repo
linked worktree, recorded branch checked out, no tracked/untracked local
state, no open PR, branch landed or exact merged head) and
`branchcleanup.delete_ticket_branch` (local `-d`/`-D` policy plus
`delete_remote_branch` gated on the merged PR at the exact remote tip). Both
take `## Dev` blackboard text. The third proof — no other non-terminal ticket
claims the branch or worktree, across every Coga workspace in the git repo —
is `commands/retire._live_checkout_claim` with its `_cleanup_checkout`
orchestration, single-consumer today. With autoclose and branch-sweep as
further consumers they qualify as shared infra under the microkernel rule
(`coga/codebase`, cited not attached: core holds code with ≥2 real
consumers): move them into `branchcleanup` or a sibling module. Never import
from `coga.commands.*` inside a sweep.

**Proofs must accept `(branch, worktree)` without a ticket.** A worklist
entry's ticket may already be deleted (retire preserved the checkout, then
removed the ticket), and a GC'd worktree may never have had one. Split or
wrap the proof functions so they take the branch and worktree path directly;
the `## Dev`-text entry point becomes a thin parser on top. The live-claim
scan still runs in every path.

**Control-branch guard.** Retire skips cleanup unless the invoking checkout
is on `cfg.git_control_branch`. `coga recurring` refuses to fire off the
control branch, and when the host checkout is elsewhere the runner services
deterministic phases from a temporary control worktree that *is* on `main`
(`recurring_runner._service_from_control_worktree`) — so under the scheduler
the guard is satisfied. A hand-run `coga run autoclose` has **no** branch
guard today: add one, and off the control branch preserve everything and
say so rather than fail.

**Destructive-behavior rule.** `coga/architecture` (cited, not attached — the
recurring-maintenance rules near its end) says deleting git refs is never
implicit, and allows a direct destructive change only when the rule is
deterministic, narrow, and named. These proofs are exactly that. The previous
design chose to only *name* the retire; this ticket reverses that on purpose
because it produced the backlog. Declare the new deletes and their proofs in
the `coga/autoclose/sweep` skill ("The retire follow-up" section), the
`coga/branch-sweep/sweep` skill, both recurring tickets' text, the
`retire_worklist.RETIRE_WORKLIST_HEADER` constant ("Autoclose only ever names
the follow-up" is no longer true), and the `retires.md` header on disk. Keep
packaged twins byte-identical
(`src/coga/resources/templates/coga/bootstrap/skills/coga/{autoclose,branch-sweep}/sweep/SKILL.md`,
`src/coga/resources/templates/coga/recurring/{autoclose-merged,branch-sweep}/ticket.md`;
`tests/test_packaging.py` enforces it). `retires.md` has no packaged twin —
do not create one.

**The ticket-owned-worktrees setting.** `[git]` is shared config
(`config.py` — `git_remote` / `git_control_branch` come from it; see
`coga.git`). Add the new key beside them with a `false` default, so a repo
that never declares it keeps the conservative behavior — destructive
behavior is never implicit, and a repo opts in by writing the assumption
down. Document the key where the other `[git]` keys are documented, and
state the assumption itself in `dev/code` → "Checkout boundary", which owns
the worktree convention (one owner per fact; `coga/architecture` may link,
not restate). Setting the key to `true` in this repo's `coga/coga.toml` is
the owner's call at the review step, not the agent's — the base prompt
forbids agents editing `coga.toml`; say so in the PR body. Autoclose's daily
path does not depend on the key: it only ever touches worktrees a ticket
recorded.

**For the peer reviewer.** The behavior change is as much in the skill and
recurring-ticket text as in the code: review the `coga/autoclose/sweep` and
`coga/branch-sweep/sweep` diffs against the proofs actually implemented, not
just the Python.

**Out of scope.** Dream; a manual `automerge` command; the paused
`v2/automerge-ticket` (agent-merged PRs — unrelated, this is cleanup after a
human merge); splitting `dev/code` into a smaller core context (the evaluator
flagged it at 64% of this ticket's composed prompt — separate ticket).

**Tests.** `tests/test_autoclose.py` and the branch-sweep tests cover the
sweeps today. Add: worktree + local + remote removed on a clean landed
checkout; each preserve reason keeps the worklist entry and names it; a
worklist entry with no ticket drains; off-control-branch hand run preserves
everything; branch-sweep removes a pristine pinned worktree and reports a
dirty or claimed one; `coga retire` unchanged after the shared-function move.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/839
branch: dispose-checkouts
worktree: /home/n/Code/coga-dispose-checkouts

## Plan (2026-09-18, implement step, attended)

Layout: separate feature checkout (linked worktree above, cut from
`origin/main` at 46362627). The primary checkout sits on another ticket's
branch (`gh-backed-readonly-context`, PR #836); control-plane writes for this
ticket stay here as the earlier steps' commits did.

Decisions taken with the owner in-session:

- Preserved entries and their refusal reasons go to Slack on **coga-important**
  (`notification.post(..., important=True)`, non-fatal): a preserved checkout is
  work a human must do. `retires.md` keeps its line format; the per-run report
  (period blackboard / stdout) carries every proof note.
- The import cycle (`autoclose` -> new disposal module -> `branchcleanup` ->
  `autoclose` parsers) is broken with one lazy import inside the autoclose
  recipe, same precedent as `step_gate.py`. Extracting the `## Dev` parsers and
  gh lookups into a leaf module is a possible follow-up, not this PR.

Shape:

- `branchcleanup`: `remove_worktree` / `delete_branch` take
  `(branch, worktree, pr_url)`; the `*_ticket_*` names stay as thin `## Dev`
  parsers. Merge authorization with no `pr:` URL falls back to merged PRs by
  head name (`prs_for_head`), the signal branch sweep already trusts.
- new `checkout_disposal.py`: `live_checkout_claim` (moved from
  `commands/retire.py`) + `dispose_checkout` (claim -> worktree -> local ->
  remote). Consumers: retire, autoclose, branch sweep.
- `autoclose`: after the sweep, dispose closed tickets' checkouts and every open
  worklist entry (all `retires.md`, ticket-less entries included); hand runs
  reconcile every worklist but record new entries only under a period task.
  Off the control branch: preserve everything, say so.
- `branchsweep`: `[git] worktrees_ticket_owned` (default false) gates removing a
  landed, pristine, unclaimed linked worktree before the existing delete path.

## Findings (implement)

- `git_repo`-harness tests (`tests/test_autoclose_dispose.py`) exercise the
  whole path for real: worktree removed, local `-d`, leased remote delete.
- The claim scan (`discover_coga_repos(root, strict=True)`) returns `[]`
  inside a recurring temp control worktree (`_is_within_control_worktree`),
  so a sweep serviced that way preserves every checkout with
  "current Coga workspace ... was not found". Not hit today: the recurring
  clone `/home/n/Code/claude/coga` sits on `main`, so the scheduler runs the
  recipe in place. Worth a follow-up if the host checkout ever moves off
  `main`. Resolved in peer review below: explicit cleanup inspection now
  permits this root while scheduler discovery keeps its exclusion.
- Retire's `## Checkout cleanup` retro section now also carries a checkout
  whose proof *raised* (previously the exception left `worktree_result`
  None and the section was omitted). Intentional: a durable record beats a
  scrolled-away echo.
- `coga/coga.toml` (live) is untouched — the base prompt forbids it; the key
  is documented in the packaged template, `docs/operations.md`, `coga/sync`,
  and `dev/code`. Turning it on in this repo is the owner's call at review.
- Not done in this PR (possible follow-up): extracting the `## Dev` parsers
  and `gh` lookups out of `autoclose.py` into a leaf module so
  `branchcleanup` / `step_gate` / `checkout_disposal` stop importing the
  sweep module for them.

## Implement handoff (2026-09-18)

Branch `dispose-checkouts` at dae56dc4, one commit, rebased onto
`origin/main` b6e96b34 (main moved only Coga state since the branch point).
Not pushed, no PR.

What changed (34 files, +2317/-585):

- `src/coga/branchcleanup.py`: `remove_worktree` / `delete_branch` direct
  forms; `remove_ticket_worktree` / `delete_ticket_branch` are parsers over
  them. `inspect_worktree_for_removal` + `remove_inspected_worktree` split
  the structural/pristine proofs from the git removal so branch sweep can
  supply its own authorization. `_pr_cleanup_authorization(branch, pr_url=)`
  falls back to `prs_for_head(branch, "merged")` when there is no URL.
  Public `local_branch_exists`.
- new `src/coga/checkout_disposal.py`: `live_checkout_claim` (moved from
  `commands/retire.py`), `dispose_checkout`, `CheckoutDisposal`.
- `src/coga/autoclose.py`: `_dispose_checkouts` (closures + every worklist's
  open entries; control-branch guard; lazy import), `CheckoutOutcome`,
  `AutocloseResult.checkouts/disposal_skipped/disposed/preserved`,
  `retire_pending` excludes disposed closures, report renderer rewritten,
  `render_disposed_summary` (coga-flow) + `render_preserved_summary`
  (coga-important, `post(..., important=True, fatal=False)`); hand runs
  reconcile every worklist, record only under a period task.
- `src/coga/branchsweep.py`: `_remove_pinning_worktree` behind
  `cfg.git_worktrees_ticket_owned`; `worktree_removed` outcome in result,
  report, and `[branch-sweep] removed-worktree:` stdout line.
- `src/coga/config.py`: `[git].worktrees_ticket_owned` (shared only, bool,
  default false); `commands/init.py` adjusted for the 3-tuple.
- `retire_worklist.RETIRE_WORKLIST_HEADER` + live `retires.md` header.
- Text: `coga/autoclose/sweep`, `coga/branch-sweep/sweep`, both recurring
  tickets, `dev/code` (new "Worktrees are ticket-owned" subsection),
  `coga/sync`, `coga/codebase`, `coga/recurring`, packaged `coga/cli`,
  packaged `coga.toml`, `docs/operations.md`; all twins byte-identical.
- Tests: new `tests/test_autoclose_dispose.py` (dispose / preserve+important
  +worklist / ticket-less drain / claimed entry / off-control hand run),
  branch-sweep key on/off + dirty + claimed + recipe report, direct-form
  by-head-name proofs in `test_branchcleanup.py`, config key tests; retire
  tests unchanged and green after the move.

Verification: `python -m pytest` in the feature worktree — 2676 passed
(174 s). `tests/test_packaging.py` re-run after the rebase, green. Tests ran
from a throwaway `uv venv .venv` + `uv pip install -e ".[test]"` (plus `pip`,
which the wheel test needs); the venv was removed afterwards so retire can
dispose of the worktree — recreate it with those two commands to run tests
there again.

For the PR body / reviewer: the destructive change is declared in the skill
and recurring-ticket text, not only in Python; setting
`worktrees_ticket_owned = true` in this repo's `coga/coga.toml` is the
owner's call. The coga-important line is re-posted on every run while any
entry stays preserved (owner's decision this session: a preserved checkout is
work a human must do). The 10-entry backlog on the recurring clone drains on
its next `coga run autoclose`; that clone's ~33 unrecorded worktrees need the
key on plus a `coga run branch-sweep` there.


## Peer review

Codex `codex review --base main` **returned** successfully. Its three
must-fix findings were confirmed and the owner approved all three fixes:

- P1: a merged remote tip alone authorized removing a checkout with newer
  unmerged local commits. Reproduced on a disposable real Git repository;
  the directory disappeared while the local ref remained. Worktree removal
  now requires the local tip's landed proof and no open PR (including branches
  without an earlier merged PR).
- P2: a refused or failed claim scan falsely classified branch-only cleanup
  as disposed, dropping the new follow-up. Such outcomes now stay pending;
  regression tests verify reporting, important notification, and the worklist.
- P2: scheduler-owned temporary control checkouts were excluded from the claim
  scan. Explicit claim inspection now permits that root; ordinary scheduler
  discovery still excludes it. A real linked-control-worktree regression
  verifies worktree, local branch, and remote deletion.

Rebased unconditionally with `git fetch origin main` and `git rebase FETCH_HEAD`
onto 415b673f; no conflicts. Reviewed both sweep skills and recurring tickets
against the implementation, updated the local-tip/open-PR wording, and kept
packaged twins synchronized. The implementation-stage temporary-control
limitation is fixed, not deferred.

Verification complete: focused suite (branchsweep, autoclose_dispose,
workspace_discovery, retire, packaging) passed all 100 tests. Full suite
`/tmp/coga-dispose-review-venv/bin/python -m pytest` passed **2684 tests**
in 215.32 seconds. Dependencies installed
using `uv pip install --python /tmp/coga-dispose-review-venv/bin/python -e
'.[test]'`. The initial system-Python attempt failed collection because tomlkit
was missing, before the isolated environment was created.

Human-visible output: drove the report in a real PTY at 80 and 120 columns;
refusal reason and manual follow-up remained present, with ordinary line
wrapping and no cursor control. Inspected the synthetic Slack payload. This
session has no Slack UI/browser capability; the owner accepted a live
`coga slack --important` check instead. Sent a clearly labeled synthetic
preservation alert via `coga slack --task automerge/fix-let-a-lot-of-open-craps
--important --message ...`; it returned `posted` and exit 0. No production
cleanup was performed by the test.


Final handoff: `dispose-checkouts` at a59b214c (review fixes), with implementation
commit 30b0933c, two commits ahead of main. Feature checkout is clean;
`git diff --check` passed. Branch remains in the durable recorded checkout;
no PR opened in this step. No machine-local config or virtualenv was placed
in the feature checkout (only regenerable test caches remain).

`/tmp/coga-dispose-review-venv/bin/python -m coga.cli validate --json` exited 1:
222 checks passed; four existing `unsynthesized-draft-blackboard` errors on
unchanged tickets (`clean-up-all-the-working-trees`, `v2/autotrigger-ticket-type`,
`v2/measure-relay-prompt-scope-and-agent-precision`,
`v2/use-worktree-when-starting-a-dev-task`) and 53 warnings, including the
expected missing-user warning in this feature checkout. No validation repairs
were requested or applied.

## Open-PR handoff (2026-09-19, attended)

`coga open-pr` ran from the primary checkout on `main` (borrowed from
`gh-backed-readonly-context`, returned afterwards; no stash needed because both
branches carried identical bytes for the dirty task/log paths). It pushed
`dispose-checkouts` at a59b214c, opened PR #839 (non-draft, base `main`), and
recorded `pr:` above. The command's exit sweep committed the step-3 ticket state
on `main` as 3a35173b and pushed it, so the live copy is on `main`; bump ran
there. Next step is the owner-controlled review gate: merge, plus the
`worktrees_ticket_owned` decision for `coga/coga.toml`.

## PR

Merged tickets currently leave their checkouts behind until someone manually
runs retire. Autoclose now disposes of recorded linked worktrees and branches
under the shared retire proofs and retries open `retires.md` entries, including
entries whose tickets were deleted. Refusals remain visible in the worklist,
run report, and a coga-important notification on each run.

Weekly branch sweep can also remove pristine, unclaimed linked worktrees when
`[git].worktrees_ticket_owned = true`. The default is false. Removal requires
the local tip to have landed and no open PR; an older merged remote tip never
vouches for newer local work. Both sweeps share claim checks across the
checkout's Coga workspaces, including recurring temporary control checkouts.
Skills, recurring templates, contexts, and packaged twins describe the deletes
and their proofs; manual retire keeps the same cleanup path.

Owner action at review: this PR deliberately does not change this repo's
`coga/coga.toml`. Enable `worktrees_ticket_owned = true` there only after
accepting the ticket-owned-worktree assumption. Each sweep only cleans linked
worktrees of its invoking clone; run the recurring cleanup from
`/home/n/Code/claude/coga` after the change is installed there.

Test plan: `/tmp/coga-dispose-review-venv/bin/python -m pytest` — 2684 passed;
`git diff --check` passed; report preview in a real PTY at 80/120 columns and
an owner-approved synthetic `coga slack --important` delivery test passed.
`python -m coga.cli validate --json` reports four existing draft-blackboard
errors on unchanged tickets (plus warnings); no new structural error was found.
