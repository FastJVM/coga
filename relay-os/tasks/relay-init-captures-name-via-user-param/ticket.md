---
title: relay init captures name via --user param
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

Revise the open, unmerged work in PR #391 (from `marketing/relay-init-captures-name`)
so `relay init` takes the operator's name as a `--user NAME` parameter instead of
the interactive prompt that PR introduced. `relay init --user zach` writes `user`
to `relay.local.toml` (validated: non-empty, no `"` or `\`); a bare `relay init`
errors and asks for the flag; `relay init --update` is unchanged. This keeps init
scriptable — Nico's review ask — while still leaving `current_user` valid the
moment init finishes. Also update PR #391's description to match the param flow.

## Context

- Origin: Nico's only review comment on PR #391 — "no prompt; pass it as a param
  instead please (so we can script the init)." Settled with Nico (2026-06-18):
  `--user` param, no prompt, and no auto-detect from `git config`/`$USER`.
- Lands on the existing PR, not a new one. Do the work on branch
  `init-captures-name-impl` (#391's branch; worktree
  `/Users/zach2179/Desktop/relay-init-name-impl`), push to update #391, and
  `gh pr edit` its body. The owner merges #391 after — do not open a second PR.
- Code: the init prompt added in #391 — the `init._prompt_user_name()` call in
  `_do_init` (`src/relay/commands/init.py`) — becomes a `--user` option read with
  the same validation. `setup._ensure_user` keeps its shared prompt for the
  onboarding path (name capture is **not** moved to `relay setup`/`build` —
  decided against). `relay init --update` already skips name capture; leave it.
- Bare `relay init` with no `--user`: error with a clear "pass `--user NAME`"
  message rather than writing `user = ""`. With prompt and auto-detect both ruled
  out, the flag is required for a fresh init.
- Relationship: this revises the deliverable of `marketing/relay-init-captures-name`
  (currently at its human-review step) before merge. That ticket's other scope —
  stamping out `new-user`, the empty/filled gate, the browser-automation
  placeholder — stays as implemented in #391; only the name-capture mechanic changes.
