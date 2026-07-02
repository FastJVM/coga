---
slug: coga-cli-cutover
title: coga CLI cutover
status: draft
mode: llm
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: coga/cutover
  steps:
  - name: cutover
    skills: []
    assignee: agent
  - name: verify
    skills: []
    assignee: agent
  - name: fan-out
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (cutover)
---

## Description

Cut the team over from the `relay` CLI to `coga` once the rename PR (#454)
merges: reinstall the package and switch every `relay`→`coga` invocation on
each checkout/machine, verify no `relay-os/` directory resurrects on the fresh
`coga` main, then close the rename ticket and fan out to the in-flight sibling
branches and the host-repo migration.

**Why:** the rename is breaking — package, command, import, and on-disk dir all
become `coga`. A lingering pre-rename `relay` process re-creates a stray
`relay-os/`, and the ~15 other branches / ~10 host repos break against the new
CLI, so the cutover has to be coordinated. Launch this immediately after the merge.

## Context

- Source rename lands via PR #454 (`rename/relay-to-coga`); the diff is green
  (924 tests) — the work here is sequencing, not code.
- The `relay` command on a dev box is usually a shell-function wrapper plus an
  editable `relay-os` install; both get replaced in the `cutover` step.
- Repo-rename-gated follow-ups (URL flips, PyPI publish, migrate tooling) live in
  `coga-rename-follow-ups-post-repo-rename` — separate from this immediate cutover.
- No mergeability watcher is running: if #454 shows conflicts at merge time,
  re-sync first — `git merge origin/main` in the worktree, relocate any new
  `relay-os/tasks/*` adds to `coga/tasks/`, then push.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
