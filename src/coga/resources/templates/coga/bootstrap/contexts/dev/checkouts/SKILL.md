---
name: dev/checkouts
description: Where code-ticket work runs: the two supported checkout layouts, the sandbox clone fallback, seeding and restoring a fresh checkout, and which checkout to invoke Coga from.
---

# Feature checkouts

Choose a layout when the branch is created and record it in `worktree:`
([dev/dev-record](../dev-record/SKILL.md)); every later step reads that line.
Retiring checkouts is covered in
[dev/checkout-cleanup](../checkout-cleanup/SKILL.md).

## Two layouts

- **Separate feature checkout.** The primary checkout is the control-plane
  checkout, kept on `main` when possible. Code changes happen in a feature
  worktree outside it. Blackboard and `## Dev` writes, `coga bump`,
  `coga slack`, `coga block`, and `coga open-pr` run in the primary checkout
  on the control branch; `open-pr` pushes the recorded branch by name and never
  enters the feature checkout. Commit any task-state changes separately from
  the code PR. `code/open-pr` calls this the legacy layout, meaning the older
  supported shape, not a deprecated one.
- **Single checkout.** `worktree:` names the primary checkout itself; the agent
  stays on the recorded feature branch for code and control-plane work. The
  feature-branch ticket is the live copy: write `## Dev`, bump, and open the PR
  there without switching back. `open_pr._checkout_mode` recognizes this when
  the recorded worktree is this same checkout, it is not a linked worktree,
  and `COGA_EXPECTED_TASK` proves the session owns the ticket. Do not
  `git add` the live task, log, or recurring state there.

**The agent moves itself.** `coga launch` never chooses a working directory
(`repl_supervisor.run_with_done_marker` takes no `cwd`; `src/coga/` has no
`os.chdir`). The session inherits the cwd `coga launch` was typed in. Launch
reads `worktree:` only to validate checkout and assist scope. Every "change
into the feature worktree" instruction is the agent's to carry out and verify;
in the separate layout an edit made before moving lands in the control
checkout.

**Sandbox clone fallback.** When the sandbox mounts the primary `.git`
read-only so `git worktree add` fails, make `git clone --no-hardlinks` under
`/tmp`, repoint `origin` at the real remote, fetch the control branch, and
record the clone's path in `worktree:`. It is a separate-checkout variant:
`_checkout_mode` cannot prove ownership from a foreign repository, so
control-plane writes, bump, and `open-pr` stay in the primary checkout. Do not
force writes through protected metadata or stop to ask when this fallback is
available.

**Keep it durable.** A `/tmp` checkout dies at reboot. For multi-session work
use a sibling path (`../coga-<branch>`) or push the branch before ending the
session; an unpushed branch whose only checkout is under `/tmp` is one reboot
from unrecoverable.

## What a fresh checkout lacks

A fresh linked worktree or clone has nothing Git ignores:

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
- **One branch, one checkout.** `git worktree add` refuses a branch another
  worktree holds.

Copied config, rebuilt `.agent-skills/`, and discovery links are ignored,
non-regenerable state, so they make `coga retire` preserve the checkout.

## Which checkout you invoke Coga from

- **Mutating commands publish from wherever they run.** The exit sweep
  (`sync_coga_state`) publishes every dirty path under `coga/tasks/`,
  `coga/log.md`, and `coga/recurring/` to control, even after a config
  failure; contexts, skills, workflows, and config are never swept. Commit
  deliberate ticket prose on the control branch before running a mutating
  command from a feature checkout. Which invocations sweep is owned by
  [coga/sync](../../coga/sync/SKILL.md).
- **`coga launch <target> --prompt-report` writes.** It sweeps like any launch
  and regenerates `.agent-skills/`. For a write-free view call
  `compose.compose_prompt_report` or `compose.compose_prompt` directly.
- **Launch and megalaunch compose from the invoking checkout.** Run them only
  from a control checkout freshly synced to `origin/<control>`; a stale one
  re-dispatches merged work.
