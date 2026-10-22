---
name: coga/checkouts/sandbox-clone
description: The sandbox clone fallback for a read-only primary `.git`, and what a fresh clone lacks — `coga.local.toml`, agent discovery links, `.coga/` — and how to seed it.
---

# Sandbox clone fallback and fresh checkouts

Part of [coga/checkouts](../SKILL.md).

## Sandbox clone fallback

A managed agent sandbox may allow source edits while mounting the primary
`.git` read-only. The fallback is an independent clone (`git clone
--no-hardlinks` under `/tmp`, `origin` repointed at the real remote, the
control branch fetched) on the ticket's branch, recorded as `worktree:` next
to the unchanged `branch:`. Ticket state, `coga bump`, and `coga open-pr` stay
in the primary checkout on `main`; `open-pr` runs its git checks inside the
recorded clone. Never force writes through protected metadata. A `/tmp` clone
dies at reboot, so push the branch before ending the session.

- **Recorded clone.** Launch from the primary keeps it on control with the
  authoritative ticket, verifies the clone is a checkout on the recorded
  branch, and names it in the runtime notice; change code only there. A
  missing clone or one on another branch refuses: recover or re-record it,
  never let launch replace it.
- **Manual session.** When creating the branch fails because metadata is
  read-only, make the clone and create the branch there:

  ```bash
  feature_clone_dir=$(mktemp -d /tmp/coga-feature.XXXXXX)
  git clone --no-hardlinks "$(git rev-parse --show-toplevel)" "$feature_clone_dir/repo"
  git -C "$feature_clone_dir/repo" remote set-url origin "$(git remote get-url origin)"
  git -C "$feature_clone_dir/repo" fetch origin main
  git -C "$feature_clone_dir/repo" switch -C main FETCH_HEAD
  git -C "$feature_clone_dir/repo" switch -c <branch-name>
  ```

  Record that clone's repo path as `worktree:` next to `branch:` and publish
  the record from the primary ([manual](../manual/SKILL.md)); seed its local
  config (below), then work in the clone. If the clone or its fresh fetch
  fails, escalate: ask the attending human, or in a queue run
  `coga block --task <slug> --reason "<capability or access needed>"`.
- **First refusal after launch switched.** Launch prepared and switched the
  primary on the host, then the agent's first Git write (a commit) is
  refused. The primary may stay on the prepared branch until host recovery
  succeeds; the recorded-clone entry guarantee did not hold this session.
  The agent stops implementation writes, names the failed operation, records
  the branch and its OID, and preserves verified copies of all staged,
  unstaged, untracked, and ticket work outside the repo. It may make a
  preservation clone but does not continue there, allocate another branch,
  bump, or signal completion. It asks the attending human to finish from a
  permitted host shell after ending the session (an unattended session
  escalates the missing capability). On exit, launch's normal return
  returns a clean or already-published primary; source dirt refuses and
  stays intact. On the host, following
  [reconciliation](../reconciliation/SKILL.md):
  1. Create or verify an independent clone of the prepared branch at its
     actual tip, keeping its unique commits; transfer the source changes
     with byte, mode, and deletion checks. Never copy ignored credentials,
     and never commit the ticket projection.
  2. Verify the backups and the clone, then clear only those proven copies
     from the primary. Publish or reconcile saved primary ticket state
     without replaying any lifecycle command, and use the ordinary return
     (`coga run publish-state`, then the manual end-of-step return) to reach
     a clean, current control.
  3. Only then verify the clone's remote, branch, and retained work, seed
     its local config, write `worktree:` beside the unchanged `branch:`,
     publish it with the exact-ticket guard, and confirm it on control.
  4. Relaunch the same step; the recorded-clone path keeps the primary on
     control.

  An interrupted or refused stage keeps its backups, clone, branch, and
  notes, names what remains unpublished, and stops: a candidate clone is not
  linkage until published. There is no in-session host control, automatic
  dirt migration, or compensating transition.

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
  cannot be imported, it re-execs under the `coga` console launcher's interpreter
  (the shebang on POSIX, the embedded interpreter in a Windows wheel launcher). The
  source config must parse with a nonempty `user`; an absent destination is copied
  byte-for-byte; an existing one must have the same actor. On POSIX the helper
  restricts both to mode `0600`. On Windows it preserves the user directory's
  inherited access controls, without applying POSIX modes. It verifies the file
  is ignored and untracked; never
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
