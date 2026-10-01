---
name: coga/uninstall
description: What `coga uninstall` removes from a repo, including a relocated contexts directory, what it preserves, and how `--purge` handles the global package.
---

# `coga uninstall [--yes] [--purge]`

The inverse of `coga init`: it removes this repo's Coga footprint so trying
Coga is reversible (`src/coga/commands/uninstall.py`). It removes files from
the working tree and commits nothing; commit or discard the removal like any
other change. Git history remains the recovery source.

## What it removes

The plan is gathered read-only first (`_build_plan`) and printed:

- `coga/`, the whole Coga tree;
- the **configured contexts directory** when `[layout] contexts` places it
  outside `coga/`. The whole configured root is Coga-owned state, including
  any non-context files a repo keeps there
  ([coga/context-layout](../context-layout/SKILL.md));
- the agent skill symlinks `.claude/skills/coga` and `.codex/skills/coga`,
  pruning `skills/` and the agent directory only if left empty;
- `CLAUDE.md` / `AGENTS.md` that still match the shipped guide byte for byte.
  Edited guides are renamed to `<name>.coga-bak`, not deleted;
- the coga-managed block in the host `.gitignore`.

It asks for confirmation unless `--yes` (`-y`) is passed. With nothing to
remove and no `--purge`, it says so and exits.

## Safety rules

- **Layout.** Uninstall only undoes the standard init layout, a `coga/`
  subdirectory. A repo whose `coga.toml` sits directly at the checkout root
  is refused rather than guessed at.
- **Relocated root resolution.** `_configured_contexts_root` applies the
  same checkout-root anchoring and containment rules as config load
  (`resolve_layout_contexts_path`). It does not require the directory to
  exist or be trackable, because uninstall is also the recovery path for a
  broken install. If `coga.toml` or `[layout]` cannot be resolved safely, the
  plan prints a warning and leaves any relocated directory in place. Invalid
  config never makes uninstall guess an external destructive target.
- **Order.** The external contexts root is removed before `coga/`, because
  `coga.toml` is the durable record of where it lives. A failure there stops
  with the installation intact and retryable.

## The global package

Without `--purge`, the `coga` package stays installed (it serves every repo
on the machine) and the command prints `uv tool uninstall coga` /
`pipx uninstall coga` / `pip uninstall coga`. With `--purge`, it uninstalls
through the installer that owns the running CLI's venv, detected by
`running_cli_location` (`src/coga/commands/update.py`) from a marker in the
unresolved `sys.executable` venv root:

- `uv-receipt.toml` (the preferred `uv tool install coga`,
  [coga/install](../install/SKILL.md)) → `uv tool uninstall coga` with
  `UV_TOOL_DIR` set to the venv root's parent, so a nondefault tools
  directory is targeted even when `$UV_TOOL_DIR` is now unset or different.
  A uv tool venv normally has no pip, so pip is never tried there;
- `pipx_metadata.json` → `pipx uninstall coga`;
- anything else → `<python> -m pip uninstall -y coga`.

If the installer is missing from `PATH` or the uninstall fails, it prints the
same installer's manual command (for uv, prefixed with that `UV_TOOL_DIR=`).
