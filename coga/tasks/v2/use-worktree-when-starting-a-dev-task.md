---
slug: v2/use-worktree-when-starting-a-dev-task
title: use worktree when starting a dev task
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/codebase
- coga/sync
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decisions (bootstrap interview)

- **Worktree vs branch-in-repo:** chose worktree. Decided by concurrency — we
  run dev tasks in parallel, and a single checkout can't keep two agents from
  colliding on one working tree. (Relay's `git.py:sync_task_state` already
  supports a feature-branch path that lands task-state on the control branch
  via working-tree-free plumbing, so worktrees and the control plane coexist.)
- **Real problem is litter, not worktrees.** Two causes: (1) no fixed location
  — `dev/code/SKILL.md` only says "outside the primary checkout," so agents
  dump into `~/code`; (2) no cleanup trigger.
- **Path convention:** `<repo>/worktree/<slug>`, keyed by slug. Must be
  gitignored (root + shipped template `.gitignore`) since it sits inside the
  primary checkout.
- **Scope:** folded cleanup INTO this ticket. `autocleanup-worktree-branche`
  (empty sibling draft) is superseded — close on review.
- **Workflow:** `code/with-review` (not `dev/with-self-review`) — git-lifecycle
  code with medium failure radius wants a peer pass + owner gate.
- **Contexts:** relay/codebase, relay/sync, dev/code.

## Autonomy triage

- Tier: **human-verify** (verifiable + bounded, but medium failure radius —
  a bad `git worktree remove --force` can delete real work). Expressed via
  `code/with-review`'s owner gate before merge.
- Q1 documented: yes — desired behavior (create at fixed path, clean up on
  done/merge) is concrete.
- Q2 conventional enough: yes — mechanical lifecycle feature.
- Q3 verifiable/bounded: yes — pytest + manual, scoped to relay's git layer.

## Evaluator review

Assessment complete. Here is my cold review.

**1. Description clarity (could a no-context agent start?)**
- Mostly yes for the *creation* half: the path (`<repo>/worktree/<slug>`), the blackboard `## Dev` lines, and the rationale (concurrency) are all concrete.
- The *cleanup* half is deliberately under-specified: the ticket punts the mechanism ("implement step should pick the mechanism... flag it on the blackboard if it needs a design call"). That's a defensible delegation, but it means the agent inherits an open design question, not a spec. For a `code/with-review` ticket that's borderline — see scope below.
- Ambiguities an agent will hit: (a) **What is `<repo>`?** In this repo the git root and `relay.toml` root can differ — `_toplevel` vs `cfg.repo_root` (git.py:498-524 explicitly calls this out: `cfg.repo_root` "may itself be `relay-os/`, not the git root"). The ticket says "inside the primary checkout" but never says which root anchors `<repo>/worktree/`. This matters for both the gitignore path and the worktree-remove call. (b) **"optionally the merged branch"** — leaves branch deletion as the agent's call with no criterion. (c) **Who creates the worktree today?** The ticket says "agents scatter worktrees" — implying it's a manual agent action driven by the `code/implement` skill, not relay CLI code. But the cleanup proposal ties into `relay mark done`/`relay automerge` (CLI code). So creation stays a convention (markdown) while cleanup becomes code — an asymmetry the agent must reconcile and the ticket doesn't name.

**2. Does `code/with-review` fit?**
- Reasonable fit. The change is real code (`mark.py`/`automerge.py` cleanup hook or a new `relay worktree` helper) plus a context-doc edit, with a medium failure radius. The ticket's own justification for peer review over self-review (a bad `git worktree remove` could delete real work) is sound.
- Mild mismatch: the workflow is PR-centric (`open-pr`, mergeable-conflict resolution, owner gate). Part of this ticket is a pure markdown context edit (`dev/code/SKILL.md`) — fine to ride along, but if cleanup lands as a design-call deferral, the `implement` step may stall and need `relay panic`, which the workflow supports but the ticket should anticipate.

**3. Attached contexts**
- `dev/code` — directly relevant; it's the doc being changed. Correct.
- `relay/sync` — relevant and the ticket does the right thing by *also* copying the load-bearing fact into `## Context` (the `sync_task_state` feature-branch landing path coexists with worktrees; don't break it). Good practice. One gap: the real interaction risk isn't sync — it's that a worktree at `<repo>/worktree/<slug>` makes the git root contain a nested working tree, and `git add -- <pathspec>` / `git rev-parse --show-toplevel` behavior from *inside* the primary checkout is unaffected, but `git status` in the primary checkout will list `worktree/` unless ignored. That's the gitignore point — well flagged.
- `relay/codebase` — appropriately broad for "this is a change to relay's own source layout." Fine as an orientation context; no specific fact needed copying.
- Nothing critical missing, but a pointer to `automerge.py` / `mark.py:mark_done` (the actual cleanup hook sites) would have saved the agent a search.

**4. Scope**
- It bundles **three** things: (a) name the path in the context doc, (b) creation convention change, (c) cleanup mechanism (new code), and it explicitly **folds in a sibling ticket** (`autocleanup-worktree-branche`). That sibling is an empty stub (`status: draft`, no description, no workflow) — so folding it in is low-cost consolidation, not absorbing real planned work. Defensible.
- The risk isn't ticket-count, it's that cleanup is the open-ended part ("pick the mechanism / may need a design call") riding in the same PR as a trivial doc edit. If the design call is non-trivial (lifecycle hook into `automerge`/`mark done` vs a standalone `relay worktree` command), this is closer to two tickets. I'd flag: consider landing the path+gitignore+context change first (mechanical, reviewable) and the cleanup-trigger mechanism second. The ticket as written allows both in one shot.

**5. Assumptions worth questioning before launch**
- **Worktree INSIDE the primary checkout is the biggest gotcha and the ticket under-flags it.** Git *permits* a worktree path inside another working tree, but it's a known footgun:
  - The gitignore line stops `git status` noise, but **`.gitignore` does not stop `git clean -fdx`** from nuking ignored dirs — an ignored `worktree/<slug>` containing real uncommitted feature work is exactly what `git clean -x` deletes. Anyone running a clean in the primary checkout torches in-flight worktrees. The ticket treats gitignore as sufficient; it isn't a full safety story.
  - Nested worktree dir interacts with **the sync overlay plumbing**: `_build_overlay_tree`/`read-tree` operate on the git root's tree. As long as `worktree/` is gitignored it won't be in the tree, so the overlay is safe — but if the gitignore is ever wrong/missing, the control-branch landing could start carrying the worktree dir. The ticket's "must be gitignored" is load-bearing for correctness, not just tidiness — worth stating that explicitly.
  - **`git worktree remove` from where?** Cleanup driven by `relay mark done`/`automerge` runs from the *primary* checkout, while the worktree may still be the agent's CWD or have uncommitted/locked state. `git worktree remove` refuses a dirty worktree without `--force`; using `--force` is precisely how you "delete real work." The deterministic-slug-removal one-liner the ticket sells as simple is the dangerous part the peer review exists to catch — the ticket should require a dirty-check / merged-check before removal, not just `remove by slug`.
  - **`<repo>` ambiguity** (above): if `<repo>` resolves to `cfg.repo_root` which can be `relay-os/`, then `<repo>/worktree/<slug>` and the `.gitignore` you must edit may not line up. The ticket edits *root* `.gitignore` and the *template* `.gitignore` but anchors the path to "the primary checkout" — pin this to the git toplevel explicitly.
  - **Two gitignores, two semantics:** root `.gitignore` ignores `worktree/` for *this* repo; the template `.gitignore` (shipped to downstream relay-os repos) would impose this layout on every consumer. That's a convention being pushed onto all users, not just a local tidy-up — a reasonable thing to flag for the owner gate, since it changes the shipped product's expected directory shape.

Net: solid, well-reasoned ticket with good context hygiene (facts copied into `## Context`, sync interaction pre-flagged). The two things I'd want resolved before/at launch: (1) pin `<repo>` to the git toplevel and confirm the gitignore path matches it, and (2) make the cleanup step's safety contract explicit (dirty/merged guard before `git worktree remove`, and the `git clean -x` exposure of in-flight worktrees) rather than trusting "remove by slug" + gitignore.

## Post-review edits

Folded the two load-bearing findings into ticket `## Context` as "Sharp edges":
pin `<repo>` to git toplevel; cleanup must guard (merged/clean) before
`git worktree remove`; gitignore is load-bearing for correctness; `git clean
-fdx` hazard; template `.gitignore` is a product decision for the owner gate.
Left open (evaluator's split suggestion): whether to land path+gitignore+doc
first and the cleanup mechanism second — noted for the implement step.
