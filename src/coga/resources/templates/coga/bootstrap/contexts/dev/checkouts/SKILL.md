---
name: dev/checkouts
description: Where code-ticket work runs: the launch checkout, launch's boundary that prepares and returns it, the manual start check and end-of-step return to `main`, the sandbox clone fallback, seeding a fresh clone, and which checkout to invoke Coga from.
---

# Feature checkouts

Code-ticket work runs in the checkout the session was launched from. There are
no linked worktrees and no control checkouts for ticket work: every code step
starts on `main` and ends on `main`, and the feature branch is only checked out
while code is being changed. Under `coga launch` the launcher performs both
moves; in any other session the agent does. Linked worktrees left over from an
earlier layout are still disposed of by `coga retire` and autoclose
([dev/checkout-cleanup](../checkout-cleanup/SKILL.md)); nothing creates new ones.
The one alternative checkout is the sandbox clone fallback below.

`origin` and `main` stand for the configured `[git].remote` and
`[git].control_branch`; `coga/tasks/`, `coga/recurring/`, and `coga/log.md`
for the configured workspace's task, recurring, and log paths.

## The launch boundary

An ordinary ticket launch prepares the invoking checkout before it reads the
ticket to compose, run `ticket.py`, or activate, and returns it after every
agent session or `ticket.py` phase and at teardown. Where the boundary sits in
dispatch and chaining is owned by [coga/launch](../../coga/launch/SKILL.md).
Each time it:

1. **Publishes routine state.** The ordinary state sweep (`sync_coga_state`)
   lands any dirty `coga/tasks/`, `coga/recurring/`, and `coga/log.md` path
   the session or script did not publish. Only what publication cannot land
   stays dirty.
2. **Pins control.** `git fetch origin main` and pin that commit. Local
   `main` must exist and be equal to or behind it. A detached HEAD, a merge,
   rebase, cherry-pick, revert, or bisect in progress, `main` ahead of or
   diverged from `origin/main`, or `main` checked out in another worktree
   refuses (remedy: `git pull --rebase` and push, or
   `git worktree remove <path>`).
3. **Proves every change.** Staged, tracked, and untracked changes anywhere
   in the checkout are examined. Only Coga state may be discarded, and only
   when already on the pinned `origin/main`: the same existence, file mode,
   and bytes, or, for a `merge=union` file such as `coga/log.md`, every working
   line already on control (union-merging it onto control changes nothing).
   A staged copy must equal HEAD's or the published one. Deletions and both
   sides of a rename count separately. Symlinks, submodules, and mode
   changes refuse even with equal bytes. Ignored files are never candidates;
   one the move would overwrite refuses.
4. **Mutates only after full proof.** The whole plan is re-observed just
   before the first write, and changed evidence refuses. Then proven tracked
   paths are restored to HEAD, proven untracked files removed, HEAD switched
   to `main`, and `main` fast-forwarded to the pinned commit; the result is
   verified clean at that commit. It never stashes, resets hard,
   force-switches, deletes a branch, or pushes code. The feature branch stays.

An entry refusal names the blocking paths or branch and the remedy, starts no
work, changes no checkout contents or local ref, and exits 75 so the outer
sweep does not publish the rejected dirt. A refusal after a session is a
prominent warning: the remaining work and the session's own result stand,
chaining stops, and that command's end sweep is withheld. An unexpected Git
or I/O failure after mutation began reports where it stopped; nothing is
rolled back. A killed launch is recovered by the next entry.

The boundary is skipped, and the checkout left as it is, for Git-disabled,
non-Git, and remote-less workspaces (no freshness is claimed); bootstrap and
chat targets, including delegated bootstrap sessions; `--prompt-report`; a
launch from the ticket's recorded `worktree:` on its recorded `branch:` (the
recorded human assist and the sandbox clone); a ticket holding a released
megalaunch admission; and megalaunch picks. Recurring periods keep their own
entry gates, which already require control, and get the return half,
including a period that delegates to a bootstrap target: the delegated
session itself is exempt, but its period settles once that session ends. A
refusal there exits 75 so the recurring sweep stops launching templates.

## Start, work, end

### In a launched session

`coga launch` sets `COGA_LAUNCH_RETURNS_CHECKOUT=1` in the session only when
it prepared the checkout and will return it.

1. **Confirm entry.** HEAD is `main`, clean (`git status --porcelain
   --untracked-files=all` prints nothing), at `origin/main`. Anything else
   means stop and escalate: ask the attending human, or `coga block` in a
   queue run.
2. **Work.** Record `branch:` on `main` and publish it (below), then switch to
   the feature branch and change code there. Commit only code: stage paths by
   name, never `git add -A` or `commit -a` over Coga state. Test, commit,
   rebase onto `origin/main`, push.
3. **Hand off from the branch.** The branch's copy of the ticket predates
   what was published on control, so load control's copy first:
   `git fetch origin main && git restore --source=origin/main --worktree --
   <task path>`. Do not stage it. Write the handoff, then run `coga bump`
   last; it publishes the ticket and log. Do not return to `main`: launch
   does that after the session. A bump that prints `[git] sync failed` or
   `sync refused` left the handoff unpublished, and launch's return will
   refuse over it; say so in the session rather than discarding it.

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
   - for every dirty path under `coga/tasks/`, `coga/log.md`, and
     `coga/recurring/`, verify it is already on `origin/main` by the rules of
     the launch boundary above (`git diff --quiet origin/main -- <path>`;
     for `coga/log.md`, every added line is on `origin/main`) and discard it
     (`git restore --source=HEAD --staged --worktree -- <path>`). `git diff`
     skips untracked files, so compare an untracked one with
     `git show origin/main:<path> | cmp - <path>` and delete it only when
     identical;
   - `git switch main`, then `git merge --ff-only origin/main`.

   If any dirty Coga-state path is *not* already on `origin/main`, or any
   other path is dirty, stop and escalate. Never discard unpublished state.
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
edits with the existing state sweep, using a Python interpreter that imports
the installed Coga package (see [coga/testing](../../coga/testing/SKILL.md)):

```sh
python -c 'from coga.config import load_config; from coga.git import sync_coga_state; sync_coga_state(load_config())'
git status --porcelain --untracked-files=all
```

Require the status output to be empty before switching. The sweep reports
publication failures without raising, so its exit code alone is not proof.
If the tree remains dirty, stop and escalate; do not switch, stash, or commit
the ticket edit on the feature branch. The same publication applies to a
sandbox clone's `worktree:` record in the primary checkout, before starting
work in the clone.

**Sandbox clone fallback.** When the sandbox mounts the primary `.git`
read-only so `git switch -c` fails, make `git clone --no-hardlinks` under
`/tmp`, repoint `origin` at the real remote, fetch the control branch, create
the branch there, and record the clone's path in `worktree:`
([dev/dev-record](../dev-record/SKILL.md)). Ticket state, `coga bump`, and
`coga open-pr` stay in the primary checkout on `main`; `open-pr` runs its git
checks inside the recorded clone. Do not force writes through protected
metadata or stop to ask when this fallback is available. A `/tmp` clone dies
at reboot, so push the branch before ending the session.

## What a fresh checkout lacks

A fresh sandbox clone has nothing Git ignores:

- **`coga.local.toml`: hard error.** Commands that act as someone (`bump`,
  `block`, `create`, `mark`, `launch`, `run`, `slack`, ...) load with
  `require_user=True` and exit 2 before acting; read-only views (`status`,
  `show`, `validate`, `usage`, `skill status`, `recurring list`,
  `secret get`) tolerate it. No variable or flag substitutes. Seed it
  immediately after creating the checkout and on every resumed session:

  ```bash
  python /resolved/code/implement/seed_local_config.py /primary/repo/coga /feature/repo
  ```

  Resolve the attachment from the primary checkout's local skills, else the
  package (`python -c 'from coga.paths import packaged_template_path;
  print(packaged_template_path("bootstrap", "skills", "code", "implement"))'`
  under an interpreter that imports `coga`). Start the helper with Python
  3.11+; it imports `tomllib` before reaching the re-exec fallback. If `coga`
  cannot be imported, it re-execs under the `coga` script's interpreter. The
  source config must parse with a nonempty `user`; an absent destination is copied
  byte-for-byte with mode `0600`; an existing one must have the same actor and
  is tightened to `0600`. It verifies the file is ignored and untracked; never
  symlink, print, stage, or commit it. Remove it on teardown only for
  disposable checkouts whose owning flow removes the checkout.
- **Agent discovery links do not self-heal.** Launch rebuilds
  `coga/.agent-skills/`, but the ignored `.claude/skills/coga` and
  `.codex/skills/coga` links are created only by `coga init`. From this repo's
  checkout root, inspecting existing paths first:

  ```sh
  mkdir -p .claude/skills .codex/skills
  ln -s ../../coga/.agent-skills .claude/skills/coga
  ln -s ../../coga/.agent-skills .codex/skills/coga
  ```

- **`.coga/` is created on demand** (run records, megalaunch selection).
  `.venv/`, `.env*`, `.secrets/` are not needed: `coga` runs from its own
  install and `env:` refs read the process environment.

A rebuilt `.agent-skills/` and an unedited copy of `coga.local.toml` do not
block `coga retire` of a leftover linked worktree; an edited copy and discovery
links are ignored, non-regenerable state, so they make it preserve the checkout.

## Which checkout you invoke Coga from

- **Mutating commands publish from wherever they run.** The exit sweep
  (`sync_coga_state`) publishes every dirty path under `coga/tasks/`,
  `coga/log.md`, and `coga/recurring/` to control, even after a config
  failure; contexts, skills, workflows, and config are never swept. Write
  deliberate ticket prose on `main`, not on a feature branch. Which
  invocations sweep is owned by
  [coga/sync](../../coga/sync/SKILL.md).
- **`coga launch <target> --prompt-report` writes.** It sweeps like any launch
  and regenerates `.agent-skills/`. For a write-free view call
  `compose.compose_prompt_report` or `compose.compose_prompt` directly.
- **Launch and megalaunch compose from the invoking checkout.** An ordinary
  ticket launch brings it to a fresh control checkout first (the launch
  boundary above). Run megalaunch and exempt launches only from a control
  checkout freshly synced to `origin/<control>`; a stale one re-dispatches
  merged work.
