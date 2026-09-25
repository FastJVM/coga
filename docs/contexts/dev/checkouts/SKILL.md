---
name: dev/checkouts
description: Where code-ticket work runs: the launch checkout, the start check and end-of-step return to `main`, the sandbox clone fallback, seeding a fresh clone, and which checkout to invoke Coga from.
---

# Feature checkouts

Code-ticket work runs in the checkout the session was launched from. There are
no linked worktrees and no control checkouts for ticket work: every code step
starts on `main` and ends on `main`, and the feature branch is only checked out
while code is being changed. Linked worktrees left over from an earlier layout
are still disposed of by `coga retire` and autoclose
([dev/checkout-cleanup](../checkout-cleanup/SKILL.md)); nothing creates new ones.
The one alternative checkout is the sandbox clone fallback below.

## Start, work, end

1. **Start check.** Before anything else, `git fetch origin main`, then require
   HEAD on `main` (the configured control branch), a clean tree with Coga state
   included (`git status --porcelain --untracked-files=all` prints nothing),
   and a successful `git merge --ff-only origin/main`. `coga launch` publishes
   its own `launched` audit line before the agent starts, so a clean tree is
   the normal case. (Launch also regenerates the ignored
   `coga/.agent-skills/` view; a repo initialized before `coga init` wrote
   that ignore rule sees it as dirt — add `.agent-skills/` to
   `coga/.gitignore`, never commit it.) Anything else — dirty files, another
   ticket's branch, a diverged `main` — means stop: ask the attending human,
   or `coga block` in a queue run. Do not work around an occupied checkout with a
   linked worktree, a control checkout, a stash, or a switch.
2. **Work.** Write any ticket state you need while still on `main` (plan,
   blackboard notes), publish it as described below, then create or switch to
   the feature branch and change code there. On the branch, edit code only:
   ticket and blackboard edits made on a feature branch are not published
   until the next sweep, so the end procedure would find them unpublished.
3. **End.** Commit, push the branch (`git push -u origin <branch>`, or
   `--force-with-lease` after a rebase), then return:
   - `git fetch origin main`;
   - for every dirty path under `coga/tasks/`, `coga/log.md`, and
     `coga/recurring/`, verify its working bytes equal `origin/main`'s
     (`git diff --quiet origin/main -- <path>`) and discard it
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

`origin` and `main` stand for the configured `[git].remote` and
`[git].control_branch`.

Steps that only read the branch — peer review's first pass, open-pr — never
switch: `git diff main...<branch>` and `git log main..<branch>` read it by
name, and `coga open-pr` pushes it by name from `main`. A step that then needs
to change code (fixes, a rebase) follows start/work/end above.

**The agent moves itself.** `coga launch` never chooses a working directory
(`repl_supervisor.run_with_done_marker` takes no `cwd`; `src/coga/` has no
`os.chdir`). The session inherits the cwd `coga launch` was typed in, which is
the checkout it works in.

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
  under an interpreter that imports `coga`). Any `python` may run it; it
  re-execs under the `coga` script's interpreter when needed. The source
  config must parse with a nonempty `user`; an absent destination is copied
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
- **Launch and megalaunch compose from the invoking checkout.** Run them only
  from a control checkout freshly synced to `origin/<control>`; a stale one
  re-dispatches merged work.
