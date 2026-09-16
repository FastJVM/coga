---
title: State which branch is canonical for machine-generated Coga state
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

`coga/contexts/coga/sync/SKILL.md` (~67 KB) documents the *mechanism* of
cross-branch task-state sync exhaustively — `sync_task_state`'s narrow pathspec
and cross-branch land, `sync_log` leaving feature-branch audit commits local,
`open-pr`'s dual publish, the state-regression guard,
`refresh_coga_state_from_control`'s launch-end pull-back — but nowhere states
the *policy* those mechanisms serve.

The policy exists and was settled by the owner on 2026-08-25, and it lives only
in a draft ticket body (`coga/tasks/stop-syncing-task-state-onto-the-feature-branch.md`,
`## Context`): machine-generated Coga state and audit history are canonical on
the control branch; a feature checkout may mirror them while a session runs, but
the mirror is operational state, not review payload; hand-authored contexts,
skills, workflows, config and ticket prose remain ordinary feature work even
when the catch-all sweep committed them. A grep of the sync context finds no
occurrence of "canonical", "review payload", or "mirror".

The cost of the omission is concrete. `coga/tasks/detect-stranded-ticket-writes-across-checkouts.md`
re-derives the surface from scratch and states as a "verified code fact" that
"Nothing ever pushes those files back into the feature worktree's working tree",
naming `git._try_update_local_ref` as "core's only cross-checkout ref
reconciler" — while the sync context's own launch-end pull-back section
describes a second reconciler that, when launch is invoked from a feature-branch
checkout, overlays and commits control's changed `coga/tasks/**` onto that
branch. That ticket's entire divergence discriminator rests on the invariant it
got wrong.

## Context

Add a short policy subsection to `coga/contexts/coga/sync/SKILL.md` (and its
enforced packaged twin): which side is canonical, what the feature-side mirror
is for, and which reconcilers write into which checkout. That last item is what
would have stopped the stranded-writes design from building on a false
invariant.

Re-verify the reconciler behavior against `src/coga/git.py` and the launch-end
pull-back path before writing — the point of this ticket is to stop the fourth
re-derivation, so it must not add a fifth wrong one.

A separate Dream proposal PR from this run also edits the sync context (root-layout
pathspecs, best-effort delivery exceptions, cadence surfaces, and the
mutating-experiment rule). Check whether it has merged and rebase rather than
conflict.

<!-- coga:blackboard -->

## Dev

branch: sync-canonical-policy
worktree: /home/n/Code/claude/coga-sync-canonical-policy

Separate-checkout layout: linked worktree off `main`; `## Dev` and `coga bump`
live in the primary checkout.

## Implement — 2026-09-16

**Description was partly stale.** The grep in the description no longer holds:
"mirror, not review payload" and "canonical on the control branch" already sat
at the top of `### The feature-branch publication boundary` (landed with the
boundary work, #806-era). What was still missing was the *inventory* — which
writers reach which checkout — and the policy as a section of its own rather
than a lead-in to one mechanism. So not an already-satisfied close.

**Dream proposal PR:** no open PR touches `coga/contexts/coga/sync/SKILL.md`
and its topics (root-layout pathspecs, best-effort delivery, cadence,
mutating-experiment rule) are already in the file on `main` — it has merged.
No conflict.

**Re-verified against code before writing** (module + symbol):
- `git._try_update_local_ref` / `git._worktree_holding_branch`: bare
  `update-ref` when no worktree holds the control branch, else
  `merge --ff-only` run *through* that worktree. Only ever reaches the control
  branch's holder. Callers: `git._land_on_control_branch`,
  `git._land_paths_on_control_branch`, `recurring_runner` create landing.
- `git.refresh_coga_state_from_control`: control branch → ff-only; feature
  branch → overlay control's changed `coga/tasks/**`, union `coga/log.md`,
  commit on the current branch; detached → skip. Scope is
  `_toplevel(cfg.repo_root)`, i.e. the invoking checkout. Callers:
  `commands.launch` teardown (every exit path) and the recurring per-child
  preflight (`require_control_verification=True`).
- `git._reconcile_feature_payload`: after a feature-branch landing, moves the
  invoking checkout's HEAD onto the accepted control commit (soft reset or
  merge) — the one place control's product tree enters a working tree.

So the precise invariant: a feature checkout receives control state only via
commands run *inside* it (writer 1 mid-run, writer 3 at launch end). The
stranded-writes ticket's "nothing ever pushes those files back into the
feature worktree" is false exactly when `coga launch` is invoked from that
worktree, and true for a worktree whose commands all run from primary.

**Change:** new `### Policy — the control branch is canonical` subsection
before the publication boundary (three policy bullets + three-writer
inventory + corollary). Boundary section's opening now points at the policy
instead of restating it (one owner per fact). Both twins byte-identical.

**Tests:** `python -m pytest` in the worktree — 2561 passed. Rebased onto
`origin/main` (unchanged, `7317811a`). Commit `e888dcc5`.

**Adjacent finding (not fixed here):**
`coga/tasks/detect-stranded-ticket-writes-across-checkouts.md` still asserts
the false invariant (its "verified code fact" around
`git._try_update_local_ref` being the only cross-checkout reconciler, with
stale `git.py` line numbers). Its divergence discriminator needs re-deriving
against the new policy subsection before that ticket proceeds.
