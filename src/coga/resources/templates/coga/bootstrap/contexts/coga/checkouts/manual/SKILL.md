---
name: coga/checkouts/manual
description: The start check, branch work, and end-of-step return an agent performs itself when launch did not prepare its branch, and how to publish pre-branch ticket edits before switching.
---

# Manual start, work, end

Part of [coga/checkouts](../SKILL.md), which owns the launched lifecycle and
which checkout each step starts in.

## Procedure

Use this when no `COGA_LAUNCH_RETURNS_CHECKOUT=1` witness is set — manual or
API sessions, megalaunch picks, exempt checkouts — and before editing in a
step whose runtime notice says launch set up no branch (manual policy, or a
control step that must exceptionally change code). The agent performs both
moves:

1. **Start check.** `git fetch origin main`, then require HEAD on `main`, a
   clean tree with Coga state included, and a successful `git merge
   --ff-only origin/main`. Launch regenerates the ignored
   `coga/.agent-skills/` view; a repo initialized before `coga init` wrote
   that ignore rule sees it as dirt — add `.agent-skills/` to
   `coga/.gitignore`, never commit it. Anything else — dirty files, another
   ticket's branch, a diverged `main` — means stop: ask the attending human,
   or `coga block` in a queue run. Do not work around an occupied checkout
   with a linked worktree, a control checkout, a stash, or a switch.
2. **Work.** Write ticket state (`branch:` under `## Dev` once created with
   `git branch <name>`, plan notes) on `main`, publish it (below), then
   switch to the feature branch and change code only; ticket edits made
   there are not published until the next sweep. A resumed branch is reused:
   switch to it and `git rebase` onto fetched `origin/main`.
3. **End.** Commit, push the branch (`git push -u origin <branch>`, or
   `--force-with-lease` after a rebase), then return:
   - `git fetch origin main`;
   - for every dirty path under the Coga roots, verify it is already on
     `origin/main` by the rules of
     [the launch boundary](../launch-boundary/SKILL.md) (`git diff --quiet origin/main -- <path>`;
     for `coga/log.md`, every added line is on `origin/main`) and discard it
     (`git restore --source=HEAD --staged --worktree -- <path>`). `git diff`
     skips untracked files, so compare an untracked one with
     `git show origin/main:<path> | cmp - <path>` and delete it only when
     identical;
   - `git switch main`, then `git merge --ff-only origin/main`.

   If any dirty path under the Coga roots is *not* already on `origin/main`,
   or any other path is dirty, stop and escalate. Never discard unpublished
   state. Then write the step's handoff on `main` and run `coga bump`, which
   publishes it. The session leaves the checkout on `main`, clean.

## Publish pre-branch ticket edits

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
demand](../../state-publication/sweep/SKILL.md#strict-publication-on-demand))
is the stop signal. Use the status check only for dirty files you did not name,
and require it to be empty before switching. Do not fall back to calling the
sweep through a `python -c` one-liner: the sweep reports publication failures
without raising, and the shell's `python` often cannot import Coga at all. If
publication fails or the tree remains dirty, stop and escalate; do not switch,
stash, or commit the ticket edit on the feature branch. The same publication applies to a
sandbox clone's `worktree:` record in the primary checkout, before starting
work in the clone.
