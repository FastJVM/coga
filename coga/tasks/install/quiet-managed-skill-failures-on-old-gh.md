---
slug: install/quiet-managed-skill-failures-on-old-gh
title: Quiet managed skill failures on old gh
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

With gh < 2.90 (no `gh skill` subcommand), `coga init` prints the full `gh`
usage screen **once per managed skill** — 7 skills × ~37 lines ≈ 260 lines of
noise burying the init summary. The per-skill warning line itself is good
("GitHub CLI 2.90.0+ with `gh skill` is required … Upgrade `gh`"); the raw
`unknown command "skill"` usage dump appended to each is not. Detect the
missing/old `gh skill` **once**, print one compact upgrade line, and skip the
remaining manifest entries instead of failing each identically. With current
gh the warnings are already compact — this is only the old-gh path.

## Context

Found in the 2026-07-08 fresh-container retest with gh 2.86 (a realistic
pre-2.90 machine); reproduces Greg's original "12 noisy failure dumps"
complaint at 7. Supersedes the noise half of
`marketing/quiet-relay-init-managed-skill-failures` (relay-era draft) — the
access half is fixed (public `google/agents-cli` manifest, optional,
warn-only, works unauthenticated). Touchpoints: `src/coga/managed_skills.py`
(failure detail capture), `src/coga/commands/init.py`
(`_print_managed_skill_summary`), `src/coga/skill_manager.py` (the gh-version
probe producing the message).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
