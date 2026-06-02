---
title: auto-commit ticket state for panic and ticket-authoring edits (C)
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: codex
contexts:
- relay/sync
- relay/codebase
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

> **This is ticket C of a 3-ticket split.** A
> (`git-sync-a-helper-and-same-branch`) ships the
> `src/relay/git.py` helper + same-branch wiring + fixture. B
> (`git-sync-b-cross-branch-to-main`) adds cross-branch
> sync. **C depends on A** (and is cleaner after B); it wires the two call
> sites that A deliberately skipped because they don't go through the normal
> `slack.post()` finalizer.

## Description

A wired auto-commit+push into the clean call-site set (the logic-module
finalizers in `mark.py` / `bump.py`, plus `create`/`retire`/`recurring`).
Two state-mutating sites were deferred because they don't go through that
path. C wires them so ticket state from these commands also syncs:

1. **`relay panic`** — appends a blocker to the blackboard + log
   (`commands/panic.py:47`), no ticket.write/post finalizer.
2. **`relay ticket` authoring** — the launched bootstrap agent edits
   `ticket.md` (and blackboard) *externally* during the subprocess; relay
   never calls `ticket.write()`/`post()` for those edits, so nothing commits
   them. Commit after the session returns (around `commands/ticket.py:204`,
   after the re-read + validate).

Done looks like: after a `relay panic`, the blackboard/log changes are
committed+pushed via the same `git.py` helper; after a `relay ticket`
authoring session, the agent's ticket edits are committed+pushed.

## Context

- **Reuse A's `git.py` helper and test fixture** — C adds no new git
  mechanism, only two call sites. If B has merged, the cross-branch path is
  free; if not, C inherits A's same-branch-only behavior.

- **`relay panic` is the riskiest site** — it often fires from inside a
  feature worktree with uncommitted *code*. Scope the commit **strictly** to
  the task dir (`relay-os/tasks/<slug>/`); never `git add -A` or sweep the
  feature working tree. This is the whole reason panic was split out.

- **`relay ticket` authoring is external-edit capture** — the edits happen
  in the child agent's process, not relay's. Commit them after control
  returns and the ticket is re-read+validated (`commands/ticket.py:204`).
  Watch the empty-edit case (agent changed nothing → nothing to commit).

- **`src/relay/` work, higher review bar.** Update `example/` + `tests/`
  (extend A's git fixture to cover these two sites); run `python -m pytest`
  and `relay validate --json`.
