---
slug: cleanup/detect-the-current-git-branch-instead-of-hard-codi
title: Detect the current git branch instead of hard-coding control branch main
status: in_progress
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`coga init` writes `control_branch = "main"` into the scaffolded config
regardless of the repo's actual branch. On a machine whose `git init` creates
`master`, every subsequent Coga command prints the "control branch 'main' does
not exist (you are on 'master')" warning two or three times. Detect the
checkout's current branch at init time, or fail loud with the one-line fix.

## Context

**Reproduction** (audit, 2026-09-02): on a machine without
`init.defaultBranch=main`, `git init` makes `master`; `coga init --user tester`
succeeds and writes `control_branch = "main"`; from then on `coga status`,
`coga create`, and `coga launch` each emit the nag repeatedly. Every step of
the README quickstart is noisy for such a reader.

**Options.** Read the checkout's current branch and write that value; or keep
the `main` default but detect the mismatch during init and either offer to
rename the branch or print the exact `coga.toml` line to change. Prefer
whichever keeps the first run quiet without silently disagreeing with the
repo. Note the warning itself is correct behavior (fail loud) — the bug is
that init creates the mismatch it then complains about.

**Docs.** If the answer is documentation rather than detection,
`docs/getting-started.md` is where a reader would need it, before the init
step.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

## Dev

branch: init-control-branch
worktree: /home/n/Code/coga-init-control-branch

## Findings

- `coga init` does **not** literally write `control_branch = "main"`. The
  packaged template ships `[git]` fully commented out
  (`src/coga/resources/templates/coga/coga.toml`, the "--- Git sync ---" block);
  the value comes from the `Config.git_control_branch = "main"` default in
  `src/coga/config.py:117`.
- The nag text is `git._control_branch_mismatch_message` (`src/coga/git.py:5908`),
  emitted whenever `git._control_branch_present(root, branch, remote)` is false.
  That predicate is the exact trigger to gate the fix on.
- `git._symbolic_head` (`src/coga/git.py:5873`) already resolves the branch name
  *before the first commit* (unborn HEAD), which is precisely the
  `git init` + `coga init` case. Reused rather than reimplemented.

## Decision (confirmed with the human, 2026-09-03)

Pin the detected branch into the scaffolded `coga/coga.toml` **only when the
configured default control branch is genuinely absent** (no local ref, no
remote ref). Rationale: an unconditional pin would record a *feature* branch as
the control branch when someone runs `coga init` while on a branch of an
established main-based repo — trading one wrong config for another.

- Cannot resolve a branch (detached HEAD / git error) *and* the default is
  absent -> init still succeeds but prints the exact one-line
  `[git] control_branch = "..."` fix (human's call: loud notice, not exit 2).
- Docs: add a bullet to `docs/getting-started.md` under "A few things worth
  knowing about init" (human's call: code + docs).

Tradeoff accepted: a fresh init on a non-`main` repo now writes a real `[git]`
table into a config that previously shipped comments-only, and a later branch
rename still needs a manual edit.
