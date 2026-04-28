---
title: Reconcile recurring command spec contradiction
status: draft
mode: interactive
owner: nick
assignee: claude1
contexts:
  - relay/architecture
  - relay/principles
  - relay/codebase
  - relay/current-direction
  - relay/project-stage
workflow:
  name: code/with-review
  steps:
    - name: implement
      skill: code/implement-and-pr
    - name: review
step: 1 (implement)
---

## Description

`docs/spec.md` describes recurring scheduling two contradictory ways:

- **L684** (foreground command table) lists `relay create --check-recurring`.
- **L996** (Removed section) says `relay recurring` was *absorbed* into
  `relay create --check-recurring`, implying the standalone form is gone.

Reality: the code has only the flag form. `relay create --check-recurring`
exists in `src/relay/commands/create.py` and `relay-os/scripts/cron.sh`
calls it; running it locally returns "No recurring tasks due." cleanly.
There is no standalone `relay recurring` subcommand.

The audit (`docs/spec-audit.md` §A.1) flagged `cron.sh` as broken because
the flag wasn't documented; that diagnosis was stale by the time the audit
shipped. The real defect is the spec being inconsistent with itself.

## Context

- Audit entry: `docs/spec-audit.md` §A.1 (resolved with this direction
  during PR #43 review).
- Cron entrypoint: `relay-os/scripts/cron.sh` (calls `exec relay create
  --check-recurring`).
- Command implementation: `src/relay/commands/create.py` (look for
  `--check-recurring` flag).
- Verify before editing: run `relay create --check-recurring` from a fresh
  checkout — it should print "No recurring tasks due." or list due tasks.

## Acceptance criteria

- [ ] `docs/spec.md` L996 entry rewritten or removed so it no longer
      contradicts L684.
- [ ] L684 entry remains the canonical description (one form, one place).
- [ ] No code change unless we discover a second entrypoint that needs
      removing.
