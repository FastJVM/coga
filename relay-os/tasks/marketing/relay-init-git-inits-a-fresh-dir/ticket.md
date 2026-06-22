---
title: relay init git-inits a fresh dir
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- dev/code
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
step: 4 (review)
---

## Description

When `relay init`'s target isn't already a git repo, `_git_commit_relay_os`
returns early and silently skips committing `relay-os/` — no error, no warning —
leaving a git-backed tool untracked and half-set-up. Close the silent skip by
**failing loud** (principle 6): report that the target isn't a git repo and that
the user must run `git init` before re-running, instead of committing nothing in
silence. Do **not** auto-run `git init` — the README already directs users to
`git init` first, and letting the user run it keeps branch naming in their hands
(the `main`/`master` reconciliation is out of scope here, owned by
`fresh-repo-default-branch-mismatch-git-init-master`). Surfaced by the
fresh-directory onboarding path (`marketing/readme-and-docs`).

## Context

- The silent skip lives in `src/relay/commands/init.py` — `_git_commit_relay_os`
  returns early when `target/.git` is absent (`init.py:921`), so `relay-os/` is
  never committed and no "Committed relay-os/" line prints.
- The README's documented path runs `git init` before `relay init`
  (`README.md:42-44`), so this fires only when the user skips that step — the fix
  is a fail-loud guardrail, not a change to the happy path.
- **Decision (with zach): fail loud = hard error / non-zero exit, not a
  warning.** A warning that still exits 0 reads as advisory and is a
  failure-that-returns-success, which principle 6 forbids; the non-zero exit is
  what makes running `git init` non-optional. The message names the missing git
  repo and tells the user to run `git init` here, then re-run `relay init`.
- Note: `relay init` writes `relay-os/` to disk *before* `_git_commit_relay_os`
  runs, so a hard error at the commit step leaves `relay-os/` on disk (harmless —
  re-running after `git init` commits it). Checking git-repo-ness earlier, so a
  failed run leaves nothing behind, is optional and at the implementing agent's
  discretion.

