---
slug: on-resize-update-stauts-and-pick
title: on resize update stauts and pick
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

The interactive picker shown by `coga megalaunch` does not redraw when the
terminal window is resized: the layout stays at the old width/height until the
next keypress. Handle terminal resize (SIGWINCH) in the picker loop so the
status table and picker viewport are recomputed and re-rendered immediately on
resize — the normal behavior for a TUI.

## Context

- The picker main loop is `_pick_selection` in
  `src/coga/commands/megalaunch.py` (~line 269). It uses a Rich `Live` with
  `auto_refresh=False` and only calls `live.update(...)` after `_read_key()`
  returns, and `_read_key` (~line 252) blocks in `os.read(fd, 1)` — so a
  resize triggers no redraw.
- `_picker_view` (~line 323) already reads `console.size` fresh on every
  render, and `_picker_window` (~line 307) recomputes the viewport from row
  count — so re-rendering on resize is sufficient; no layout code needs
  changing.
- Suggested approach: install a `signal.SIGWINCH` handler for the duration of
  the picker that triggers a re-render (and restore the previous handler on
  exit). Note the handler will cause the blocked `os.read` to raise
  `InterruptedError`/EINTR depending on `signal.siginterrupt` semantics —
  handle that in `_read_key` rather than crashing.
- Reference for existing SIGWINCH handling in this codebase:
  `src/coga/repl_supervisor.py` (~line 242) installs/restores a handler and
  resizes the child PTY. Don't touch that code; it already works.
- Out of scope: plain `coga status` (`render_status` in `src/coga/views.py`)
  is a one-shot print that exits immediately — resize refresh does not apply
  to it.
- Verification is manual: run `coga megalaunch`, resize the terminal while the
  picker is open, confirm the table reflows and the viewport height adjusts.
  Automated tests for SIGWINCH delivery are brittle; a unit test around the
  key-read EINTR handling is welcome but optional.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
