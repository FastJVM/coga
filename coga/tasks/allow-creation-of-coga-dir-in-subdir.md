---
slug: allow-creation-of-coga-dir-in-subdir
title: allow creation of coga dir in subdir
status: active
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Allow `coga init` to scaffold `coga/` in a subdirectory of a host repo
(e.g. `coga init tools/ops` inside a monorepo) instead of requiring the git
root.

**Step 1 — test the current behavior** (in a throwaway repo, before writing
any code) and record the results on the blackboard:

1. `coga init <subdir>` inside a git repo — expected to refuse today:
   `_is_git_repo` (`src/coga/commands/init.py`) checks `(target/".git").exists()`,
   and a subdir has no `.git`. Confirm.
2. With a hand-placed nested `coga/` in a subdir: run `coga status` / `launch`
   from inside the subtree (should work — `find_repo_root` in
   `src/coga/config.py` walks up checking each ancestor and its direct `coga/`
   child) and from the host-repo root (expected NOT to find it — discovery
   never descends more than one level). Confirm both, and check git task-state
   sync behaves with `coga/` below the git root.

**Then fix what the test shows is broken**: relax init's git check to "inside
a git work tree" (`git rev-parse`), decide whether from-the-git-root discovery
of a nested `coga/` is in scope or documented as out, add tests for the nested
layout, and fail loud on layouts that can't work (e.g. a `coga/` inside an
existing `coga/`). If the tests show everything already works, mark the ticket
done with the evidence on the blackboard instead of changing code.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
