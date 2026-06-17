---
title: Verify recurring templates reliably instantiate under unattended cron
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

**Verification gate for v1 recurring-in-cron.** This started as a bug stub
("recurring task not instantiated?"). The underlying create-path restructure
appears to have landed in PR #357 (`57c01fa`) — recurring templates now
get-or-create a stable instantiated task at `relay-os/tasks/recurring/<name>/`
straight to `status: active`, and `tests/test_recurring.py::test_scan_due_creates_task`
covers the happy path. **Do not assume — prove it for the unattended cron
path**, because instantiation failing silently under cron is a v1 launch
blocker (the sweep would produce nothing and no human is watching).

Confirm, and only close once each is true:

1. A due template, run via a bare `relay recurring` sweep (the `cron.sh` entry
   point, **no TTY**), actually instantiates its period task on disk and
   launches it — not just in the interactive path.
2. The failure modes are covered by tests, not just the happy path: a template
   missing `ticket.md`, a malformed `schedule`, a `_`-prefixed inert dir, and a
   second sweep in the same period (dedup via `last_serviced_period`) all
   behave correctly and don't wedge the sweep.
3. If any gap remains, fix it; if fully covered, the deliverable is the
   confirming test(s) + a one-line note in the ticket that the create path is
   verified for cron.

## Context

- Reframed from a stale bug stub to a verification gate (owner decision,
  2026-06-16) — the fix is believed merged in PR #357; this ticket proves it.
- `src/relay/recurring.py` create path (`create_named` / `create_template`,
  ~lines 296–349); `relay-os/scripts/cron.sh`; `tests/test_recurring.py`.
- Pairs with `wire-recurring-sweep-into-system-cron` and
  `enforce-mode-auto-for-recurring-templates` (the other v1 cron tickets).
