---
name: dev/checkouts
description: Reconciling all agent work with moving main, where code-ticket work runs, the start check and end-of-step return, publishing pre-branch ticket edits, and which checkout to invoke Coga from; the launch boundary and sandbox clone fallback live in its leaves.
---

# Feature checkouts

Code-ticket work runs in the checkout the session was launched from. There are
no linked worktrees and no control checkouts for ticket work: every code step
starts on `main` and ends on `main`, and the feature branch is only checked out
while code is being changed. Under `coga launch` the launcher performs both
moves; in any other session the agent does. Linked worktrees left over from an
earlier layout are still disposed of by `coga retire` and autoclose
([dev/checkout-cleanup](../checkout-cleanup/SKILL.md)); nothing creates new ones
for ticket work. Two owner-accepted exceptions create linked worktrees: the
recurring runner's temporary linked control worktree for a parked checkout
([coga/internals/recurring-temp-worktrees](../../coga/internals/recurring-temp-worktrees/SKILL.md)),
and Retro's dedicated isolated checkout, which the `retro/done-ticket` skill
and `coga retire`'s task prompt create and remove for one Retro pass, so
Retro runs while the operator keeps working in the main tree (owner decision,
2026-10-14). Revisit either decision if those worktrees leak or become
operator-visible noise.
The one alternative checkout for ticket work is the [sandbox clone fallback](sandbox-clone/SKILL.md).

`origin` and `main` stand for the configured `[git].remote` and
`[git].control_branch`; `coga/tasks/`, `coga/recurring/`, and `coga/log.md`
for the configured workspace's task, recurring, and log paths. **The Coga
roots** are the Coga root plus the configured contexts root
(`git.coga_root_paths`); every eligible (unignored) file there is Coga state
that publication carries ([coga/internals/state-publication](../../coga/internals/state-publication/SKILL.md)).

## Leaves

- [dev/checkouts/reconciliation](reconciliation/SKILL.md) — keeping all agent
  edits current with main while preserving unique work.
- [dev/checkouts/launch-boundary](launch-boundary/SKILL.md) — how ordinary
  ticket launches and chat/orientation prepare and return the invoking
  checkout, how to investigate refusals, and which launches skip it.
- [dev/checkouts/sandbox-clone](sandbox-clone/SKILL.md) — the sandbox clone
  fallback and seeding what a fresh checkout lacks.

## Start, work, end

Main can advance during any session. Follow
[reconciliation](reconciliation/SKILL.md) for the shared freshness and conflict
policy, including documentation, ticket edits, and ad-hoc work.

### In a launched session

`coga launch` sets `COGA_LAUNCH_RETURNS_CHECKOUT=1` in the session only when
it prepared the checkout and will return it.

1. **Confirm entry.** HEAD is `main`, clean (`git status --porcelain
   --untracked-files=all` prints nothing), at `origin/main`. Anything else
   means stop and escalate: ask the attending human, or `coga block` in a
   queue run.
2. **Work.** Record `branch:` on `main` and publish it (below), then switch to
   the feature branch and change code there. Commit only code: stage paths by
   name, never `git add -A` or `commit -a` over Coga state. A context, skill,
   or workflow edit that belongs to the code PR (a canonical topic with a
   packaged twin, say) is committed with it before any sweeping Coga command
   runs in this checkout; left dirty, the sweep publishes it directly. Test,
   commit, rebase onto `origin/main`, push.
3. **Hand off from the branch.** The branch's copy of the ticket predates
   what was published on control, so load control's copy first:
   `git fetch origin main && git restore --source=origin/main --worktree --
   <task path>`. Do not stage it. Write the handoff, then run `coga bump`
   last; it publishes the ticket and log. Do not return to `main`: launch
   does that after the session. A bump that prints `[git] sync failed` or
   `sync refused` left the handoff unpublished, and launch's return will
   refuse over it; say so in the session rather than discarding it. The bump
   itself was recorded, so never bump again to publish it: after a
   `sync failed`, once Git access is restored, run the `coga run
   publish-state` recovery the report prints
   ([sweep](../../coga/internals/state-publication/sweep/SKILL.md#recovering-a-failed-publication)).

### Manual or API sessions, megalaunch picks, and exempt checkouts

Without the witness, the agent performs both moves:

1. **Start check.** Before anything else, `git fetch origin main`, then require
   HEAD on `main`, a clean tree with Coga state included, and a successful
   `git merge --ff-only origin/main`. Launch regenerates the ignored
   `coga/.agent-skills/` view; a repo initialized before `coga init` wrote that
   ignore rule sees it as dirt — add `.agent-skills/` to `coga/.gitignore`,
   never commit it. Anything else — dirty files, another ticket's branch, a
   diverged `main` — means stop: ask the attending human, or `coga block` in a
   queue run. Do not work around an occupied checkout with a linked worktree,
   a control checkout, a stash, or a switch.
2. **Work.** Write any ticket state you need while still on `main` (plan,
   blackboard notes), publish it as described below, then create or switch to
   the feature branch and change code there. On the branch, edit code only:
   ticket and blackboard edits made on a feature branch are not published
   until the next sweep, so the end procedure would find them unpublished.
3. **End.** Commit, push the branch (`git push -u origin <branch>`, or
   `--force-with-lease` after a rebase), then return:
   - `git fetch origin main`;
   - for every dirty path under the Coga roots, verify it is already on
     `origin/main` by the rules of
     [the launch boundary](launch-boundary/SKILL.md) (`git diff --quiet origin/main -- <path>`;
     for `coga/log.md`, every added line is on `origin/main`) and discard it
     (`git restore --source=HEAD --staged --worktree -- <path>`). `git diff`
     skips untracked files, so compare an untracked one with
     `git show origin/main:<path> | cmp - <path>` and delete it only when
     identical;
   - `git switch main`, then `git merge --ff-only origin/main`.

   If any dirty path under the Coga roots is *not* already on `origin/main`,
   or any other path is dirty, stop and escalate. Never discard unpublished state.
   Then write the step's handoff (`## Dev`, blackboard notes) on `main` and
   run `coga bump`, which publishes it. The session leaves the checkout on
   `main`, clean.

The recorded human assist and the sandbox clone keep their own rules: an
assist runs on its recorded PR branch under
[coga/internals/human-assist](../../coga/internals/human-assist/SKILL.md),
and a sandbox clone's primary checkout never leaves `main`.

Steps that only read the branch — peer review's first pass, open-pr — never
switch: `git diff main...<branch>` and `git log main..<branch>` read it by
name, and `coga open-pr` pushes it by name from `main`. A step that then needs
to change code (fixes, a rebase) follows start/work/end above.

**Launch never changes directory.** `repl_supervisor.run_with_done_marker`
takes no `cwd` and `src/coga/` has no `os.chdir`: the session inherits the
cwd `coga launch` was typed in, and the launch boundary moves only that
checkout's HEAD. It never follows a recorded `worktree:`.

### Publish pre-branch ticket edits

Writing `branch:` or plan notes on `main` does not publish them: Git carries
uncommitted edits across a branch switch. Before switching, publish those
edits strictly, naming each edited file. The recipe resolves paths against
the current directory, which launch preserves, so anchor them at the checkout
root:

```sh
coga run publish-state "$(git rev-parse --show-toplevel)/coga/tasks/<slug>.md"
git status --porcelain --untracked-files=all
```

Exit 0 means every named file is confirmed on control; any non-zero exit
(contract in [strict publication on
demand](../../coga/internals/state-publication/sweep/SKILL.md#strict-publication-on-demand))
is the stop signal. Use the status check only for dirty files you did not name,
and require it to be empty before switching. Do not fall back to calling the
sweep through a `python -c` one-liner: the sweep reports publication failures
without raising, and the shell's `python` often cannot import Coga at all. If
publication fails or the tree remains dirty, stop and escalate; do not switch,
stash, or commit the ticket edit on the feature branch. The same publication applies to a
sandbox clone's `worktree:` record in the primary checkout, before starting
work in the clone.

## Which checkout you invoke Coga from

- **Mutating commands publish from wherever they run.** The exit sweep
  (`sync_coga_state`) publishes every dirty file under the Coga roots, plus
  eligible committed state there (only routine task, log, and recurring
  state from a feature branch), to control, even after a config failure.
  Write deliberate ticket prose and knowledge edits on `main`; commit a
  knowledge edit that belongs to a code PR before running a sweeping command
  on its branch. Committing does not hold back recurring templates: committed
  `coga/recurring/` changes on a feature branch are adopted onto control by the
  next sweep (for example a `coga create` there), ahead of the code PR they
  depend on, and every later command on the branch re-adopts them, so a revert
  on control does not stick. This shipped `scope: clone` templates to main
  before the runner understood `scope:`. Make a template change that depends on
  unmerged code also work under the current control code (that fix made the
  `ticket.py` shims bump `COGA_TASK_SLUG` when set, so old code ran them as
  one-step periods), or keep the edit out of the Coga roots until the code
  lands. Leaving it uncommitted is not enough: the sweep publishes every dirty
  file there too. Which
  invocations sweep is owned by
  [coga/sync](../../coga/sync/SKILL.md).
- **`coga launch <target> --prompt-report` writes.** It sweeps like any launch
  and regenerates `.agent-skills/`. For a write-free view call
  `compose.compose_prompt_report` or `compose.compose_prompt` directly.
- **Launch and megalaunch compose from the invoking checkout.** An ordinary
  ticket launch or direct chat/orientation brings it to a fresh control checkout first (the [launch
  boundary](launch-boundary/SKILL.md)). Run megalaunch and exempt launches only from a control
  checkout freshly synced to `origin/<control>`; a stale one re-dispatches
  merged work.

## Stranded ticket writes

A ticket write committed on the feature branch strands there: control keeps
rewriting the same file at every transition. `open-pr`'s freshness gate
refuses it and `bump` warns about it on stderr. In a sandbox clone an
uncommitted ticket edit surfaces as `coga open-pr`'s "Recorded worktree has
uncommitted changes" refusal, which names this ticket's file separately.
The comparison is one-directional; a branch copy control already absorbed is
silent.

Decision (2026-10-06, owner): do not add a general cross-checkout detector for
uncommitted blackboard prose. The remaining working-memory loss is rare and
low stakes; missing checkout pointers, independent clones, detached worktrees,
and normal control-ahead divergence make reliable detection disproportionate.
Revisit if concrete lost-note incidents justify the complexity. Any future
comparison should report content the control copy lacks, without automatically
merging or overwriting either copy.

Repair: inspect the branch copy, preserve anything still needed in the primary
ticket, then restore the merge base's copy on the branch and commit:

```sh
git restore --staged --worktree --source=$(git merge-base <control> <branch>) -- <path>
```

Do not rebase to fix it, and do not restore control's copy (it goes stale at
the next transition). A dirty task/log hunk in a sandbox clone is a duplicate
only after its content is preserved in the primary ticket or verified in the
authoritative log; discard only confirmed duplicates, never commit or stash
them to pass the clean-tree gate, and never hand-edit `coga/log.md`.
This ticket's own file is never implementation diff: control has already
rewritten it, so a branch commit of it is an overlapping stranded write. Move
an intentional authored-body change to the live ticket in the primary
checkout and discard the clone's copy. `ticket.py` and attachments under
`coga/tasks/` can be implementation work and stay in the diff.
