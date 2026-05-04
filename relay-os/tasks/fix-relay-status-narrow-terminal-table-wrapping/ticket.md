---
title: Fix relay status narrow terminal table wrapping
status: done
mode: interactive
owner: nick
human: nick
assignee: nick
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
step: 2 (review)
---

## Description

`relay status` renders a Rich table that wraps very badly under ~80
columns: long titles end up stacked one character per line, making the
output unreadable in narrow terminals (split panes, tmux side panes,
small windows).

Fix: detect terminal width and either pre-truncate the title column with
an ellipsis, or fall back to a flat one-line-per-task plain format below
some threshold (e.g. <100 cols). Either is acceptable; pick the one that
keeps the wide-terminal output unchanged.

Out of scope: filters, sort options, status grouping, color tweaks. Just
the wrapping bug.

## Context

- Audit entry: `docs/spec-audit.md` §C.13.
- Implementation: `src/relay/commands/status.py` (Rich `Table` build).
- Repro: open a 60-column terminal and run `relay status` against the
  example fixture or any seeded tasks.

## Acceptance criteria

- [ ] At ≥120 cols: output unchanged from today.
- [ ] At ≤80 cols: titles truncate with `…` or render as a flat list
      (one task per line, no character-wrap).
- [ ] Test or manual repro recipe documented in the PR.
