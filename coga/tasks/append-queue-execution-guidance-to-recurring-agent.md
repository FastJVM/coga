---
slug: append-queue-execution-guidance-to-recurring-agent
title: Append queue execution guidance to recurring agent launches
status: active
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
  the terminal action for owner decisions, finish with
  bump/mark done/block).
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

**Shipped before this ticket was activated.** The work was done in an attended
orient session on 2026-07-20 on branch `claude/recurring-queue-guidance`;
PR [#623](https://github.com/FastJVM/coga/pull/623) merged to `main` at
2026-07-21T19:11:52Z as commit `0b22fdab`. Verified 2026-07-21 that every
checklist item above is live on `main`:

- **New package resource** — `src/coga/resources/prompt-queue.md`: the
  recurring counterpart of `prompt-megalaunch.md` (announce-and-continue,
  `coga block` as the terminal action for owner decisions, worktree-fallback
  note, finish via bump/mark done/block). Ships automatically because
  hatchling packages `src/coga/resources/**`; `tests/test_packaging.py:15`
  lists it in `EXPECTED_BOOTSTRAP_RESOURCES`.
- **Hidden `--queue-guidance` flag** — `src/coga/commands/launch.py:126-128`
  declares the option (mirroring `--return-timeout`); line 500 appends
  `_queue_prompt_suffix()` to the composed prompt when it is set, riding the
  existing `prompt_suffix` seam on `spawn_agent_session`. The suffix loader
  raises `ComposeError` if the resource is missing. Script launches are
  unaffected (no composed prompt); manual `coga launch` is unchanged
  (default `False`).
- **Recurring passes `queue_guidance=not interactive`** — both call sites are
  present: `src/coga/recurring_runner.py:518` (sweep) and `:679`
  (`_launch_created` / named launch). The sweep, `--force`, and on-demand
  `recurring launch <name>` (including the `coga dream` alias) get the
  guidance; `--interactive` human-stepped debugging runs stay plain.
- **Packaged `coga/cli` context** — the **Queue guidance** paragraph is in the
  recurring section of
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`.

Tests added: sweep passes `True` / interactive passes `False` / named launch
passes `True`; a suffix-content unit test; the packaging manifest entry. One
existing strict-signature fake was updated to accept and assert the new kwarg.
Verified with `python3.12 -m pytest` → 1374 passed, 1 skipped.

Because there was no branch, diff, or PR left to create, this ticket was closed
via the already-satisfied path rather than running the remaining
self-qa/pr/review steps.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
