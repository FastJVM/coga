---
title: Fix coga git sync failures that leave main diverged from origin
status: draft
owner: nicktoper
contexts:
  - coga/sync
  - coga/internals/state-publication
workflow: code/design-then-implement
---

## Description

Coga's automatic git sync keeps failing, and when it does it leaves local main with commits that diverge from origin/main. On 2026-09-29 this forced a manual reset. Find the root causes, mainly a read-only .git inside agent sandboxes, and fix them so that sync either succeeds or fails loudly without leaving main diverged.

Done when:

- The root cause of each failure class above is either fixed or explicitly
  accepted, and the reason is written down.
- A launched Codex session and a launched Claude session can each finish a
  step without adding a `[git] sync failed` line.
- A failed sync never leaves `main` diverged when origin already has the same
  content. Any failure it does produce is loud and says what to run.

## Context

### Incident (2026-09-29)

The incident and all log evidence below come from the Multiply checkout
(`~/Code/multiply`, its `coga/log.md`), a consumer repo of this package; the
fix lands here in Coga.


Local `main` was 1 commit ahead of `origin/main` and 5 behind, and it also had
uncommitted edits to `coga/log.md` and the `decide-the-six-title-only-tickets-flagged-by-valid`
ticket. The local commit `94da4bda` and the uncommitted edits had already
reached origin through separate sync commits (`f1f696a8` "Sync coga state",
`6ab1e663`, `f500316f`, `b8953733`, `b37922f7`). The working tree was
byte-identical to `origin/main`. It was fixed by hand with
`git branch backup/main-94da4bda HEAD && git reset origin/main`. Nobody should
have to do that.

### Sync failures recorded in `coga/log.md` (`[git] sync failed`)

| Count | Error | Dates | Likely cause |
| --- | --- | --- | --- |
| 151 | `git fetch` → `Could not resolve host: github.com` | 2026-08-14 → 2026-09-21 | Session without network access (sandbox) |
| 40 | `git hash-object` → `unable to create temporary file: Read-only file system` / `fatal: Unable to add (null) to database` | 2026-09-22 → 2026-09-29 | `.git` mounted read-only in the agent sandbox (seen around codex-held steps) |
| 4 | `git add` → `Unable to create '/home/n/Code/codex/multiply/.git/index.lock': Read-only file system` | 2026-08-26 | Same cause, in the `~/Code/codex/multiply` checkout |
| 16 | `could not rebase 'main' onto origin/main: could not apply 1678fe5... Contexts: pivo…` | — | A real rebase conflict that kept recurring |
| 2 | Rebase blocked by untracked working-tree files | — | Untracked files at paths that upstream commits add |
| 4 | `could not reapply local changes after rebasing`; pre-sync state restored | — | Conflict between the autostash and upstream |

`[coga]` is the slug on 89 of the failures, which makes them repo-wide state
syncs. Every other failure belongs to a ticket-scoped sync.

### What to find out

1. Which agent/sandbox configuration makes `.git` read-only or cuts off the
   network during a launched session. Codex is the prime suspect because its
   workspace-write sandbox is known to protect `.git`. Check `[agents.*]` in
   `coga.toml` / `coga.local.toml`. Agents may not edit those files, so
   propose the change to the owner.
2. Why a failed in-session sync ends up as a later local commit that
   duplicates what reached origin another way, rather than being retried
   cleanly. `coga/sync` and `coga/internals/state-publication` are attached.
3. Whether the divergence could be avoided: for example, sync from the
   supervisor (outside the sandbox) after the session exits, or have a
   post-failure sync notice that local content already matches origin and
   fast-forward.
4. Whether the recurring rebase conflict (`1678fe5`) and the untracked-file
   blocks are still live or already resolved.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
