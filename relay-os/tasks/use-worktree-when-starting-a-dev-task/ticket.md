---
title: use worktree when starting a dev task
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/codebase
- relay/sync
- dev/code
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
---

## Description

Make dev-task code work happen in a dedicated git worktree at a
deterministic, slug-keyed path, and clean that worktree up when the task
finishes. Today `dev/code/SKILL.md` only says "a path outside the primary
checkout," so agents scatter worktrees into `~/code` next to real repos and
nothing ever removes them. The result is litter that accumulates forever.

Two halves, both in scope for this ticket:

1. **Creation** — when a dev task starts, create the feature worktree (and
   branch) at `<repo>/worktree/<slug>` instead of an ad-hoc location. Record
   `worktree:`/`branch:` on the blackboard `## Dev` section as the convention
   already requires.
2. **Cleanup** — remove the worktree (and optionally the merged branch) when
   the task reaches `done` / the PR merges, so nothing is left behind.

Worktrees are the right call because we run dev tasks concurrently — multiple
agents must not collide on one working tree. The only real cost is the litter,
which deterministic placement + automatic cleanup fixes.

## Context

**This is a change to relay's own behavior**, not a one-off. Read
`relay/codebase` for source layout and `relay/sync` for how control-plane git
sync works — worktree lifecycle intersects with it (`git.py:sync_task_state`
already has a feature-branch path that lands task-state on the control branch
via working-tree-free plumbing, so worktrees and the control plane already
coexist; don't break that). `dev/code` is the context whose "Checkout
boundary" section currently encodes the vague convention and must be updated
to name the exact `<repo>/worktree/<slug>` path.

**Path convention:** worktrees go at `<repo>/worktree/<slug>` — keyed by task
slug so cleanup is a deterministic one-liner (`git worktree remove` by slug).
Because this dir sits *inside* the primary checkout, it MUST be added to
`.gitignore` (root `.gitignore`, and check the shipped
`src/relay/resources/templates/relay-os/.gitignore`) or the control-plane
checkout will see every worktree as untracked clutter — recreating the exact
mess we're fixing.

**Reliability of cleanup is the whole point.** The current failure mode is
"agent forgets to delete." A convention that just *tells* the agent to remove
the worktree will fail the same way. Prefer a mechanical trigger tied to a
lifecycle event — e.g. removal driven by `relay mark done` / `relay automerge`
or a small `relay` worktree helper — over relying on the agent to remember.
The implement step should pick the mechanism; flag it on the blackboard if it
needs a design call.

**Sharp edges (resolve at implement time, surfaced by ticket review):**

- **Pin `<repo>` to the git toplevel**, not `cfg.repo_root` — `git.py:_toplevel`
  notes `repo_root` may be `relay-os/`, not the git root. The worktree path and
  the `.gitignore` you edit must anchor to the same root (`git rev-parse
  --show-toplevel`), or they won't line up.
- **Cleanup must guard before removing.** `git worktree remove` refuses a dirty
  worktree without `--force`, and `--force` is exactly how you delete real
  in-flight work. Require a merged/clean check before removal — do not ship a
  bare "remove by slug." This safety contract is the main thing the peer-review
  step exists to catch.
- **gitignore is load-bearing for correctness, not just tidiness.** If
  `worktree/` is ever un-ignored, the control-branch overlay plumbing
  (`_build_overlay_tree`) could start carrying the worktree dir. State this in
  the convention.
- **`git clean -fdx` hazard.** A gitignored `worktree/<slug>` holding
  uncommitted feature work is exactly what `git clean -x` in the primary
  checkout deletes. Worth a note in `dev/code` so nobody torches in-flight
  worktrees.
- **The template `.gitignore` change is a product decision.** Editing
  `src/relay/resources/templates/relay-os/.gitignore` imposes the
  `worktree/<slug>` layout on every downstream relay-os repo, not just this
  one. Flag it for the owner gate.

**Supersedes** the `autocleanup-worktree-branche` draft (same author, empty
stub) — cleanup is folded in here. Close that sibling as superseded on review.

**`dev/with-self-review` exists too**, but this change wants a peer set of eyes
on git-lifecycle code (medium failure radius — a bad `git worktree remove`
could delete real work), so it runs through `code/with-review` with an owner
gate before merge.

