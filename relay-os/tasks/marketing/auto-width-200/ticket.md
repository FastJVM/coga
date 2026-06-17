---
title: auto-width-200
status: draft
mode: interactive
owner: nick
human: zach
agent: claude
assignee: nick
contexts: []
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
---

## Description

`relay status` should show every column (slug, group, status, owner, assignee,
step, mode, updated) on one line on a full terminal, instead of collapsing to a
squeezed 80-column table when it can't detect the terminal width. The fix is to
fall back to a generous width (~200) in that case while still honoring a real
terminal's detected size — see Context for the root cause.

## Context

- Lives in `src/relay/commands/status.py` — the table renders through a plain
  `Console()` (~line 75) that lets Rich auto-detect the terminal width.
- Root cause of "stuck at 80 even when I expand the window": Rich tracks the
  live window size only when stdout is an interactive TTY. When it isn't —
  piped to a pager, redirected to a file, captured by a wrapper, or some
  IDE/embedded terminals — `os.get_terminal_size()` raises and Rich silently
  falls back to its default of 80; in that state resizing changes nothing
  because Rich never re-reads the window (verified: in a non-TTY shell
  `Console().width` returns 80). So the symptom appears specifically when
  `relay status` output isn't going straight to a real terminal.
- So this is a width-fallback fix, not a new feature: stop collapsing to 80
  and use a generous width (~200) instead.
- Decision: substitute ~200 only in the fallback case — keep honoring a real
  TTY's detected size, and use the generous default only where Rich would
  otherwise collapse to 80. This preserves genuinely narrow real terminals and
  keeps the existing `NARROW_WIDTH = 100` ellipsis branch meaningful, unlike
  forcing `width=200` unconditionally (which would hard-wrap narrow terminals
  and make that branch dead code).

