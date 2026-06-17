---
title: Retire relay mark active before launch
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
---

## Description

`relay launch` already activates a ticket inline — launching *is* the readiness
signal — so requiring a separate `relay mark active` before launch is redundant.
Retire that step: stop treating `relay mark active` as a prerequisite to launch,
and scrub "run `relay mark active` first" guidance from help text, agent guides,
and docs. Decide in design whether the `relay mark active` command is removed
outright or kept as a thin convenience.

## Context

- Today `relay launch` brings a draft/paused/done ticket to `active` via
  `_auto_activate` (`src/relay/commands/launch.py`), so the old "refuse unless
  active, run `relay mark active` first" behavior is already gone for
  workflow-bearing tickets. The `relay mark active` command lives in
  `src/relay/commands/mark.py`.
- Open scope question: a workflow-less draft (`workflow: null`, what `relay
  draft` produces) still can't be activated ("no workflow, nothing to
  activate"). Decide whether retiring mark-active also means launch handles that
  case, or it stays out of scope.
- Surfaced while prototyping `relay build` (2026-06-16): the onboarding batch
  hands the human a bare `relay launch <slug>` with no mark-active step — see
  `marketing/relay-build-onboarding-flow`.
- Touch points to scrub: `AGENT_GUIDE_TEMPLATE` in `init.py` (lists `relay mark
  active <slug>`), command help text, and any workflow/docs that say to activate
  before launch.
