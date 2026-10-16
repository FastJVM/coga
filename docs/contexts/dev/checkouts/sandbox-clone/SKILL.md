---
name: dev/checkouts/sandbox-clone
description: The sandbox clone fallback for a read-only primary `.git`, and what a fresh clone lacks — `coga.local.toml`, agent discovery links, `.coga/` — and how to seed it.
---

# Sandbox clone fallback and fresh checkouts

Part of [dev/checkouts](../SKILL.md).

**Sandbox clone fallback.** When the sandbox mounts the primary `.git`
read-only so `git switch -c` fails, make `git clone --no-hardlinks` under
`/tmp`, repoint `origin` at the real remote, fetch the control branch, create
the branch there, and record the clone's path in `worktree:`. Ticket state, `coga bump`, and
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
