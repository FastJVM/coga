---
title: Add a dev worktree-setup skill for seeding relay.local.toml in fresh worktrees
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Dream 2026-W21 (knowledge scan, Phase 2) found a recurring `gap`: an agent
working in a freshly-created `git worktree` cannot run `relay validate` or
other repo-root commands, because `relay.local.toml` is gitignored and
machine-specific — it never copies into a new worktree, so the required `user`
key (and machine-local paths) are unset. Multiple done tickets rediscovered
and worked around this independently; no context, skill, or workflow step
carries the fix.

Proposal: add a small `dev/worktree-setup` skill (attachable to dev/code
workflow steps) that tells an agent entering a new worktree to seed
`relay.local.toml` — copy it from the primary checkout or create a minimal one
with at least `user` set — keep secrets out via `env:VAR_NAME` indirection, and
re-run `relay validate --json` to confirm config resolves before doing task
work.

This is a `gap` finding: the human should decide whether a skill is the right
carrier (vs. a context note, or a doc line in `relay/codebase`) and design it.

## Context

