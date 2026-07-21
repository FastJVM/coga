---
slug: append-queue-execution-guidance-to-recurring-agent
title: Append queue execution guidance to recurring agent launches
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Observed in the 2026-07-20 recurring sweep (magicator2 Dream run): mid-sweep,
the Dream agent paused the sequential queue on an interactive question to the
human ("full autonomous run?"). Attended, that worked; unattended, the
15-minute idle-timeout backstop would have torn the session down and failed
the task. `coga megalaunch` already solves this: it appends package-backed
queue guidance (`prompt-megalaunch.md`) telling the agent to announce its plan
and continue, and to end in `coga block` — never a conversational ask — when a
decision genuinely needs the owner. Recurring launches append nothing.

Fix: give recurring's automatic launches the same treatment.

- New package resource `prompt-queue.md` with sequential-sweep wording
  (mirrors the megalaunch guidance: announce-and-continue, `coga block` as
  the terminal action for owner decisions, finish with bump/mark done/block).
- `coga launch` grows a hidden internal `--queue-guidance` flag (same shape
  as `--return-timeout`) that appends the resource to the composed prompt via
  the existing `prompt_suffix` seam on `spawn_agent_session`.
- `run_recurring_scan` and `_launch_created` pass `queue_guidance=not
  interactive`: the sweep and on-demand `recurring launch <name>` get the
  guidance; `--interactive` (human-stepped debugging) stays as today.
- Script launches are unaffected (no composed prompt).

Update the packaged `coga/cli` context's recurring section in the same
change.

## Context

<!-- coga:blackboard -->

## Dev

- branch: claude/recurring-queue-guidance
- pr: https://github.com/FastJVM/coga/pull/623

## Implementation notes (2026-07-20, attended orient session)

- New resource `src/coga/resources/prompt-queue.md` (recurring counterpart of
  `prompt-megalaunch.md`): announce-and-continue, `coga block` as the terminal
  action for owner decisions, worktree-fallback note, finish via
  bump/mark done/block. Ships automatically (hatchling packages
  `src/coga/resources/**`); added to `EXPECTED_BOOTSTRAP_RESOURCES` in
  test_packaging.py.
- `coga launch` hidden `--queue-guidance` flag (mirrors `--return-timeout`);
  `_queue_prompt_suffix()` loads the resource (ComposeError if missing) and
  rides the existing `prompt_suffix` seam on `spawn_agent_session`. Script
  launches unaffected (no composed prompt); manual `coga launch` unchanged
  (default False).
- `run_recurring_scan` and `_launch_created` pass
  `queue_guidance=not interactive` — the sweep, `--force`, and on-demand
  `recurring launch <name>` (incl. the `coga dream` alias) get the guidance;
  `--interactive` human-stepped runs stay plain.
- Packaged `coga/cli` context: new **Queue guidance** paragraph in the
  recurring section.
- Tests: sweep passes True / interactive passes False / named launch passes
  True; suffix content unit test; packaging manifest entry. One existing
  strict-signature fake updated to accept + assert the new kwarg.
- Verified: `python3.12 -m pytest` → 1374 passed, 1 skipped.
