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

The blackboard is a notepad to be written to often as the human and agent works through a task.
