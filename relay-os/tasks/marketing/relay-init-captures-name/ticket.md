---
title: relay init captures the user's name (kill the new-user placeholder)
status: active
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
step: 1 (design)
---

## Description

`relay init` should ask the user for their name as a scripted prompt and write
it to `relay.local.toml` (`user`), so `current_user` is valid from the very
first moment after init. Today init ships `user = ""` and defers name capture to
`relay build` / `relay setup` — but relay machinery (ticket creation, `relay
chat`, launching) is usable right after init, before any name exists. Capture at
init, then stamp that name into the delivered onboarding ticket so the
`new-user` placeholder never ships as a live value — it should not survive this
relay-build work.

## Context

- One source of truth: everything stamps owner/human from `cfg.current_user`
  (the `user` line in `relay.local.toml`) — `create_task` does
  `owner = owner or cfg.current_user` (`src/relay/create.py:55`), the onboarding
  workflow's first step sets owner/human from it, and the launch gate
  (`src/relay/config.py`) refuses if it's unset. But init's `LOCAL_TOML_TEMPLATE`
  ships `user = ""` and init never prompts.
- The gap: bootstrap machinery is usable immediately after init (`relay chat` →
  bootstrap/orient, `relay ticket` → create_task) — before `relay build`
  captures the name. Anything created or launched in that window gets an empty or
  placeholder owner.
- `new-user` lives only in the onboarding ticket template
  (`tasks/relay-setup/ticket.md`; → `relay-build` in the new design):
  `owner: new-user`, `human: new-user`. Introduced in `ba6ca2a3` (#348, the
  relay-setup scaffold). It's currently overwritten by the agent at first launch
  (soft/fragile); a human-assigned step reached before that makes `relay launch`
  die with "Agent type 'new-user' is not defined" (same class as a human-name
  assignee).
- Scope (one ticket): (1) `relay init` asks for the name (scripted) and writes
  `user`; (2) stamp that name into the delivered onboarding ticket so `new-user`
  never ships live. Once init captures it, `relay build`'s `_ensure_user` becomes
  a no-op/fallback (build requires init — `marketing/relay-build-requires-init`).
- Reverses the entry-mechanic call in `marketing/relay-build-onboarding-flow`
  ("name capture stays in the command, no prompt in init"); that bullet is
  updated. Reason: machinery usable pre-build needs a valid `current_user` at init.
- Not affected: the bootstrap items themselves (orient/project/ticket) ship
  `assignee: claude`, no owner/human, no placeholder. Related leftover worth
  scrubbing while here: `tasks/browser-automation/ticket.md` ships `owner: zach`
  hardcoded. The `_template`/recurring `replace-with-human-name` placeholders are
  fine — `create_task` overwrites them from `current_user`.
