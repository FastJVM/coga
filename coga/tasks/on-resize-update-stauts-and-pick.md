---
slug: on-resize-update-stauts-and-pick
title: on resize update stauts and pick
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
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
  the picker, restored via `try/finally` (note `_pick_selection` has multiple
  return paths: quit, enter, Ctrl-C). Important (PEP 475, Python 3.5+): a
  Python-level `os.read` does *not* raise `InterruptedError` on a signal — it
  runs the handler and retries the read, so a handler that merely sets a flag
  for the main loop will never trigger a redraw while the loop stays blocked.
  Either (a) re-render directly inside the SIGWINCH handler (it runs on the
  main thread between bytecodes; the `Live` object must be reachable), or
  (b) restructure `_read_key` around `select()` plus
  `signal.set_wakeup_fd`/self-pipe. Do not write EINTR-catching code — it
  would be dead code.
- `_read_key` toggles raw mode per keypress, so a resize can land during raw
  or cooked mode; whichever design is chosen must render correctly in both —
  test both cases manually.
- Reference for existing SIGWINCH handling in this codebase:
  `src/coga/repl_supervisor.py` (~line 242) installs/restores a handler and
  resizes the child PTY. Don't touch that code; it already works.
- Out of scope: plain `coga status` (`render_status` in `src/coga/views.py`)
  is a one-shot print that exits immediately — resize refresh does not apply
  to it.
- Verification is manual: run `coga megalaunch`, resize the terminal while the
  picker is open, confirm the table reflows and the viewport height adjusts.
  Automated tests for SIGWINCH delivery are brittle; a unit test around the
  key-read/redraw plumbing is welcome but optional.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
