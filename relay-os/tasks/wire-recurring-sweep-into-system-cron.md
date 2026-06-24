---
slug: wire-recurring-sweep-into-system-cron
title: Wire recurring sweep into system cron
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Recurring runs today only fire when a human types `relay recurring` (or
`relay dream`). The cron entry point already ships — `relay-os/scripts/cron.sh`
takes a pidfile lock and `exec relay recurring` — but nothing installs it into
an actual scheduler, so the nightly/daily sweep (digest, dream, skill-update,
autoclose-merged) does not run unattended out of the box. This is part of the
v1 launch surface: a stranger who installs Relay should get the recurring sweep
running without hand-rolling crontab.

Deliver a documented, low-friction way to schedule `cron.sh`, plus the docs to
explain it. Scope to decide during design:

- A `relay` helper to install/inspect/remove the schedule (e.g. `relay
  recurring install-cron` / `--show` / `--uninstall`) vs. docs-only with a
  copy-paste crontab line. Lean toward a helper that writes the user crontab
  entry idempotently and prints what it did, since the manual line is easy to
  get wrong (absolute repo path, `cd`, log redirect).
- Cadence default (hourly is safe — the pidfile lock makes overlapping runs a
  no-op) and how the user overrides it.
- Honor the "Relay does not manage cron itself" stance from the roadmap: if we
  add a helper it should be an explicit opt-in command that the user runs, not
  something `relay init` silently wires up.
- Surface the no-TTY constraint: only `mode: auto` / `mode: script` templates
  launch under cron; an interactive template scaffolds but fails to launch.
  Cross-reference / depend on `enforce-mode-auto-for-recurring-templates`.
- README / install-doc section so the install story (Wave 1) covers "and here
  is how you turn on the recurring sweep."

Acceptance: from a fresh install, a documented single step results in
`cron.sh` firing on a schedule and at least one `mode: auto`/`script` recurring
template producing its expected output (e.g. a digest post) unattended.

## Context

- `relay-os/scripts/cron.sh` — the existing entry point (pidfile lock + `exec
  relay recurring`). Its header already documents the intended crontab line.
- `relay/recurring` context — the recurring lifecycle/contract.
- Roadmap Wave 1 (installability / launch gate) and Wave 2
  `nightly-auto-drain-run-for-ready-tickets`, which also "wires
  `relay-os/scripts/cron.sh`; Relay does not manage cron itself." Keep this
  ticket scoped to *scheduling the sweep*; the budget-aware auto-drain loop is
  separate.
- Related: `enforce-mode-auto-for-recurring-templates` (no-TTY safety).

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
