---
name: coga/init
description: What `coga init` does for a fresh repo versus a clone of a repo that already uses Coga, what it writes and seeds, and how it records the operator's name.
---

# `coga init`

`coga init [PATH] --user <name>` adopts Coga into an existing Git project. It
belongs in the real project, not an empty scratch directory: Coga lives in
the same repo as the work it organizes. Starting a brand-new project means
`git init` first. The command (`src/coga/commands/init.py` `_do_init`) takes
one of two paths depending on whether `PATH/coga/coga.toml` already exists.

## Fresh repo

Every precondition is checked before anything is written, and each failure
exits 2 with the remedy:

- `git` is on `PATH`;
- `--user` is given, non-empty, with no `"` or `\` (Coga never guesses a
  name from Git or `$USER`);
- `PATH` is inside a Git work tree (it need not be the root: `coga init
  tools/ops` scaffolds a nested `tools/ops/coga/` in a monorepo);
- the host repo does not gitignore the target `coga/`;
- Git can author a commit (`git var GIT_AUTHOR_IDENT` and
  `GIT_COMMITTER_IDENT` both succeed);
- the target is not already inside another Coga repo (the walk up stops at
  the first `.git`). A `coga/` without `coga.toml` is refused as broken or
  foreign.

Then init:

1. Copies the packaged template tree (`src/coga/resources/templates/coga/`)
   into `coga/`, skipping `bootstrap/`
   (`src/coga/commands/update.py` `copy_fresh_templates`). The result is
   `coga.toml`, `context.md`, `log.md`, `tasks/`, `recurring/`, `skills/`,
   `workflows/`, a `contexts/` holding only the `_template/` scaffold and its
   `.gitignore`, plus `coga/.gitignore` wrapped in a coga-managed block.
   Bundled contexts, skills and workflows are **not** copied. They resolve
   from the installed package after the local roots miss
   ([coga/context-layout](../context-layout/SKILL.md)).
2. Relocates `contexts/` only if the scaffolded `coga.toml` itself sets
   `[layout] contexts` (the shipped template does not). The destination must
   not already exist or be ignored.
3. Seeds the `coga-build` onboarding ticket only when the target was empty
   (nothing but `.git`, `.DS_Store`, and init's own outputs) and is not a
   nested init. A filled repo has it pruned. `owner: new-user` placeholders
   are stamped with your name.
4. Writes `coga/coga.local.toml` (gitignored) with `user = "<name>"`.
5. Pins `[git] control_branch` when the default `main` is absent and Git
   makes the answer unambiguous: the unborn HEAD of a ref-less repo with no
   remote, or an established repo's cached remote default branch. It never
   contacts the remote and never promotes the feature branch you happen to be
   on. A detached HEAD, or an established repo with no cached default, leaves
   `main` in place and prints the `[git]` lines to verify.
6. Builds `coga/.agent-skills/` and symlinks `.claude/skills/coga` and
   `.codex/skills/coga` to it; adds a coga-managed block to the host
   `.gitignore`; writes `CLAUDE.md` and `AGENTS.md` only where missing
   ([coga/agents](../agents/SKILL.md)).
7. Commits the new `coga/` (and any generated host files) and prints the
   SHA. Pushing is up to you.

Init is atomic: any failure before the commit, including Ctrl-C, removes the
partial `coga/` and any relocated contexts, so a re-run is not wedged. A
failed commit itself (a hook, odd repo state) does not roll back. It warns
with the exact `git add`/`git commit` commands to finish.

Init installs no software. It builds no virtualenv, installs no package or
skill, makes no `gh` call and writes no `PATH` shim. It is offline and cheap,
so an editable checkout can scaffold a scratch repo without publishing a
release. The printed next steps are: put `coga` on `PATH` if it is missing;
edit `coga.toml`; install an agent CLI; then `coga build` (empty repo) or
`coga ticket "<title>"` (filled repo).

## Clone of a repo that already uses Coga

A clone carries the committed `coga/` but none of the gitignored,
machine-local half: `coga.local.toml`, the agent skill symlinks, and
`coga/.agent-skills/`. The same command creates exactly that:

```sh
git clone <repo> && cd <repo>
coga init --user <your-name>
```

This path (`_setup_initialized_clone`) stages and commits nothing. It wires
the agent skill links first. If that fails, it exits non-zero and leaves the
local config untouched. Fix the reported path and re-run; correct links
from an earlier attempt are reused. Then it writes `user`. A missing file
gets the full template. An existing `coga.local.toml` is edited in place as
TOML, so other keys, nested tables and comments survive; `user` is a
top-level key, and table entries also named `user` are left alone. An
unparseable local file is a hard error. Without `--user` it fails naming the
flag. Once `user` is set, re-running init is refused with the upgrade menu:
upgrade via the owning installer, fix or remove a broken `coga/`, or
`coga uninstall`.

## The operator's name

`user` in `coga.local.toml` is the name tickets and agents use for you. It is
never inferred, because a wrong guess fails quietly against ticket `owner:`
tokens. Read-only surfaces (`coga status`, `show`, `validate`, `usage`,
`--help`, `skill status`, `recurring list`, `secret get`) load config with
`require_user=False` and work without it; `coga validate` warns
(`missing-user`) until it is set. Everything that creates or moves work fails
with `Run coga init --user <name>`.

Discovery: commands find the repo by walking up for `coga.toml`, also
checking a sibling `coga/` at each level. A nested Coga repo is only found
from inside its own subtree (`src/coga/config.py` `find_repo_root`).
