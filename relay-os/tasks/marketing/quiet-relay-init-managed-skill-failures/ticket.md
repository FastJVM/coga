---
title: Quiet relay init managed-skill failures
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

On a fresh `relay init` where `gh` can't run `gh skill` (needs 2.90.0+, which
many users won't have — and `gh skill` may not even be GA yet), all ~12
*optional* managed skills fail and each prints the **entire `gh` usage block**.
A newcomer's very first command then spews 12 walls of error text and buries the
"Initialized / Committed relay-os" success lines — it reads as broken when it
isn't. Collapse the optional-skill failures into one concise line (count + the
`gh` upgrade hint + the `relay skill install …` remediation) instead of
repeating a full usage dump per skill. "Fail loud" shouldn't mean "fail 12× and
hide the success."

## Context

- Output is the problem, not behavior: optional-skill failures are non-fatal —
  init still writes and commits `relay-os/`. The per-skill loud print is
  `src/relay/commands/init.py` `_print_managed_skill_summary` (~L472–485), fed by
  `install_managed_skills`; the `gh skill` requirement is `skill_manager.py:32`.
- Surfaced running the fresh-directory onboarding flow on `gh 2.88.1` (Homebrew):
  12/12 optional skills failed, each dumping `gh`'s full command list.

