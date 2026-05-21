---
title: Make relay panic exit non-zero
status: done
mode: interactive
owner: nick
human: nick
agent: nick
assignee: nick
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement-and-pr
  - name: review
---

## Description

`relay panic` currently exits 0. That's wrong: panic is the agent's
distress signal, and a parent shell or supervising agent reading the exit
code has no way to tell a panicked child from a clean one. It should exit
non-zero (1 is fine) so wrappers can react.

Scope is tight: change the exit code only. Don't touch the panic message,
the Slack mention, the log entry, or the ticket status. The ticket
remains in whatever state panic puts it in today (the audit confirmed
status is left untouched — no auto-paused).

## Context

- Audit entry: `docs/spec-audit.md` §C.8.
- Implementation: `src/relay/commands/panic.py`.
- Anyone shelling out to `relay launch ... && next-step` today sees panic
  as success and proceeds — that's the bug the exit-code fix unblocks.

## Acceptance criteria

- [ ] `relay panic` exits with a non-zero status (`1`).
- [ ] All other panic side effects unchanged (Slack mention, log line,
      ticket status).
- [ ] Test asserts the exit code.
