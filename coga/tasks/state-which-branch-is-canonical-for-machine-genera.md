---
slug: state-which-branch-is-canonical-for-machine-genera
title: State which branch is canonical for machine-generated Coga state
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
