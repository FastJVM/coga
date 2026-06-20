---
title: make recurring --all a real full run, drop the debug-sandbox machinery
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/cli
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
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

`relay recurring --all` is currently built as a "debug sandbox": it spins up
throwaway `<template>-dbg-<timestamp>` scratch task dirs, suppresses git
sync and Slack notifications by detecting the `-dbg-` slug, auto-reaps
orphaned scratch dirs, and folds each run's outcome back into the template
`log.md`. That sandbox framing was a **misunderstanding** — `--all` was only
ever meant to **force a real, full run of every recurring template, ignoring
the schedule and the status filter**. Nothing more.

Worse, the sandbox is a leaky half-measure: isolation is enforced by the task
*slug* (`is_debug_slug`), but workers that reach a fixed global path bypass it
entirely. Concretely, a `--all` sweep on 2026-06-18 **posted a real digest to
Slack and drained the real production spool**, because `run_digest` resolves
`digest_spool_path(cfg)` → the real `recurring/digest/` dir and calls
`post(cfg, message, task_path=spool_path.parent)`, neither of which is gated
by `is_debug_slug`. Dream's debug child tasks (`dream-debug-validate-drift`,
etc.) also leaked into the spool because their slugs carry no `-dbg-` infix.

So the run is neither hermetic nor honestly real — the worst of both. Fix the
contradiction by deleting the sandbox concept: make `--all` behave **exactly
like a normal `relay recurring`** except that it bypasses the schedule and the
done/paused/in_progress status filter and runs **every** template.

### Desired behavior

- `relay recurring --all` force-runs every template under `relay-os/recurring/`
  for real: real Slack, real spool drain, real git task-state sync, real
  `last_serviced_period` advance — identical to a normal run, just forced.
- The only difference from a bare `relay recurring` is: ignore the schedule,
  and ignore the status filter that skips already-serviced / done / paused
  templates this period. A template that already ran this period is still
  re-run (force).
- No `-dbg-` scratch dirs, no slug-based suppression, no orphan reaping, no
  fold-back-to-template-log step.

### Open sub-decision for the implementer

"Force a real full run" must actually *execute* every template even when this
period's real `recurring/<name>` task is already `done`. Two coherent ways:

1. **Reuse the real period task and force-relaunch it.** `relay launch` on a
   `done` ticket already re-activates and restarts the workflow at step 1, so
   `--all` can get-or-create the real `recurring/<name>` task and force-launch
   each, with no scratch dirs at all. Preferred — simplest, fully real, reuses
   existing launch semantics.
2. Spin fresh real (non-`-dbg-`) task instances per template. Heavier; only if
   reusing the real dir causes a problem (e.g. clobbering an in-flight run).

Go with (1) unless implementation surfaces a concrete blocker; note the choice
on the blackboard.

### Scope / files (starting points, verify during implement)

- `src/relay/commands/recurring.py` — remove the debug-scratch launch path,
  `_finalize_debug_run`, `_read_debug_outcome`, `_reap_debug_orphans`, and the
  `-dbg-` slug minting; rewrite `--all` as force-run-every-template.
- `src/relay/recurring.py` — `is_debug_slug` and any debug-slug helpers, if no
  longer referenced after the above.
- `src/relay/git.py:~98-110` — drop the `is_debug_slug` git-sync suppression.
- `src/relay/notification/__init__.py:~119-130` — drop the `is_debug_slug`
  Slack/spool suppression.
- `tests/` — update/remove tests asserting the sandbox behavior; add a test
  that `--all` force-runs an already-`done`/not-due template for real.
- Docs/contexts must move in the same PR (CLAUDE.md rule): the `relay/cli`
  context's `relay recurring --all` paragraph and the `relay/architecture`
  recurring section both currently describe the disposable-scratch behavior —
  rewrite them to "forces a real full run of every template." Keep the live
  `relay-os/` copy and the packaged `src/relay/resources/templates/relay-os/`
  copy in sync.

### Verification

- `python -m pytest` green.
- Manually: `relay recurring --all` on this repo runs every template as a real
  run (real Slack post for digest, real spool drain, real `last_serviced_period`
  bump), creates no `*-dbg-*` dirs, and leaves no leftover scratch.

## Context

The 2026-06-18 sweep left these uncommitted artifacts as evidence of the leak:
`recurring/{autoclose-merged,digest,dream,skill-update}/log.md` fold-back lines
and a rewritten `recurring/digest/blackboard.md` (`posted: yes`, spool drained).
These can be discarded with `git checkout -- relay-os/recurring/` independent of
this ticket.

See `relay/architecture` (recurring primitive + the `--all` description) and
`relay/cli` (`relay recurring --all`) for the behavior being changed.
