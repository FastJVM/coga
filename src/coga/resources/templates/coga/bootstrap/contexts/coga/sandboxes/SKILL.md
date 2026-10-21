---
name: coga/sandboxes
description: "Operating agent sessions in restricted sandboxes: nested reviewers, launch environment inheritance, Git publication access, and local sandbox grants."
---

# Agent sandboxes

## Restricted sandboxes

- **Do not launch another Codex CLI from a Codex session's shell tools.**
  This nests the child inside the command sandbox, unlike Coga's supervisor
  starting the next agent after the current session exits. On Linux with
  Codex 0.162.1, the outer sandbox masks `/tmp/codex-daemon-<uid>` with mode
  `000`; the nested sandbox requires `0700` and fails before executing a
  command ([upstream report](https://github.com/openai/codex/issues/53799)).
  Retrying with escalation, `--no-daemon`, or another temporary directory did
  not resolve the observed failure. Do not treat it as evidence that the host
  socket needs a permission change. The review workflow and self-QA skill
  specify direct review in the current session. If the human explicitly
  requires the CLI reviewer, hand off for `codex review --base main` to run
  from their host shell, then inspect its returned result; restarting the
  agent and issuing the same nested command does not change the boundary.
- **A launched Codex session's shell may lack `COGA_*`.** Codex's shared
  app-server daemon runs shell commands with its own environment, so bumps
  get credited to a human and the done sentinel never fires. That is distinct
  from the nested-CLI failure above. The remedy, `launch_args = "--no-daemon"`
  under `[agents.codex]`, and the post-session warning are owned by
  [coga/agents](../agents/SKILL.md#launch-environment-inheritance).
- State-changing commands (`create`, `bump`, `mark`) write in three places a
  sandbox can treat differently: the checkout files (ticket, log), Git's
  object database (`git hash-object -w`), and the index lock
  (`.git/index.lock`). A writable checkout with unwritable Git storage saves
  the transition and fails only its publication: the `[git] sync failed`
  report names the checkout and the object directory Git resolved, which may
  be a linked checkout's shared store or a `GIT_OBJECT_DIRECTORY` override
  rather than `<checkout>/.git/objects`. Do not rerun the command. With the
  operator's authorization, rerun unsandboxed or grant write access to that
  destination (the Codex grant below covers the Git common directory), then
  run the `coga run publish-state` recovery the report prints
  ([sweep](../state-publication/sweep/SKILL.md#recovering-a-failed-publication)).
- When creating the feature branch fails because the primary `.git` is
  read-only, use the independent-clone fallback in
  [coga/checkouts/sandbox-clone](../checkouts/sandbox-clone/SKILL.md).

### Codex sandbox grant

`coga launch` spawns `codex <launch_args> <prompt>` (the shipped
`launch_args` is `--no-daemon`, which selects no sandbox policy), so a codex
session's sandbox comes entirely from codex's own config layers. In a trusted project that is
`workspace-write`: the checkout and temp dirs are writable, `.git` is
read-only, and network is off. Git sync, `git worktree add`, fetch, push,
`gh`, and `coga slack` then fail. Dream's agent capability preflight checks
for exactly these capabilities and points here. The grant that fixes this
without bypassing the sandbox lives in the repo's project-local
`.codex/config.toml`:

```toml
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
writable_roots = ["<git common dir>"]
```

- `<git common dir>` is the output of
  `git rev-parse --path-format=absolute --git-common-dir`, run in the
  checkout the codex session starts in: the directory Git writes to and the
  one Dream's preflight probes. Do not substitute `<checkout>/.git`. In a
  linked worktree, such as the control-branch worktree `coga recurring`
  relays Dream into, `.git` is a gitfile pointing into the primary checkout,
  so granting it leaves the common dir read-only.
- The file is gitignored and machine-local: `writable_roots` needs this
  machine's absolute path. Coga ships no launch machinery for it.
- A `coga launch` preflight that warns or refuses when the common dir is not
  writable or the grant is missing was considered and left out (owner-confirmed
  plan, 2026-10-14). A write probe in the launch parent proves only the
  parent's access, not the child's effective sandbox; a check for this config
  file cannot establish child permissions, since codex permissions also come
  from other config layers and profiles; and a common-dir probe misses an
  external `GIT_OBJECT_DIRECTORY`. Dream's preflight works because it runs
  inside the launched agent. Reopening it needs its own capability design:
  where the probe runs, warn versus refuse, effective object storage, and which
  alternate configurations comply.
- Codex reads a project `.codex/config.toml` only for a trusted project
  (`[projects."<absolute repo path>"] trust_level = "trusted"` in
  `~/.codex/config.toml`, which codex's first-run trust prompt writes).
- It covers every codex session launched in that checkout, not only Dream.
- Linked worktrees share the granted common dir. Create them under an already
  writable root, such as a `mktemp -d` directory, rather than as a sibling of
  the checkout: Dream's Retro pass puts its linked checkout inside its
  temporary run directory for this reason.
- The grant takes effect in a new codex session; relaunch after editing it.
